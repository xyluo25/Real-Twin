##############################################################################
# Copyright (c) 2024-, Oak Ridge National Laboratory                          #
# All rights reserved.                                                       #
#                                                                            #
# This file is part of RealTwin and is distributed under a GPL               #
# license. For the licensing terms see the LICENSE file in the top-level     #
# directory.                                                                 #
#                                                                            #
# Contributors: ORNL Real-Twin Team                                          #
# Contact: realtwin@ornl.gov                                                 #
##############################################################################
'''
class to host Network element of Abstract scenario
'''
from pathlib import Path
from unittest import result
import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import os
import shutil
from shapely.geometry import Polygon
import math
import pyufunc as pf
import warnings
import subprocess


class Network:
    """The Network class to host the Network element of Abstract scenario
    """
    def __init__(self, output_dir: str = None):
        self._output_dir = output_dir
        self.NetworkName = "network"
        self.NetworkVertices = ""
        self.ElevationMap = "No elevation map provided!"
        self.OpenDriveNetwork = OpenDriveNetwork(output_dir=self._output_dir)


def create_sumo_net_from_vertices(net_name: str, net_vertices: list[tuple[float, float]], output_dir: str) -> bool:
    """ Create SUMO Network From Vertices Using OSMRoad Class, download from OpenStreetMap.

    Note:
        This function will create a sub-directory 'OpenDrive' in the output_dir to save the generated SUMO network files.

    Args:
        net_name (str): The name of the network.
        net_vertices (list[tuple[float, float]]): The list of vertices defining the network boundary.
        output_dir (str): The output directory to save the generated network files.

    Returns:
        bool: True if the OpenDrive network is created successfully, False otherwise.
    """

    # TDD
    if not isinstance(output_dir, (Path | str)):
        raise ValueError("output_dir must be a string or a Path object")

    if not Path(output_dir).exists():
        os.makedirs(output_dir, exist_ok=True)

    # create OpenDrive directory in output directory
    opendrive_dir = pf.path2linux(os.path.join(output_dir, 'OpenDrive'))

    # create output directory if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Delete existing OpenDrive directory and its contents
    if os.path.exists(opendrive_dir):
        shutil.rmtree(opendrive_dir)

    # Create new OpenDrive directory
    os.makedirs(opendrive_dir, exist_ok=True)

    current_dir = os.getcwd()

    try:
        # create networkx graph network
        nx_net = OSMRoad(output_dir=output_dir)
        nx_net.get_graph(net_vertices)
        nx_net.add_spread()
        nx_net.add_num_lane()
        nx_net.add_missing_value()
        nx_net.generate_edges()
        nx_net.generate_nodes()

        # change director to opendrive directory
        os.chdir(opendrive_dir)

        # get node and edge path
        path_node = pf.path2linux(os.path.join(output_dir, 'OpenDrive/nodes.nod.xml'))
        path_edge = pf.path2linux(os.path.join(output_dir, 'OpenDrive/edges.edg.xml'))
        path_net = pf.path2linux(os.path.join(output_dir, f'OpenDrive/{net_name}.net.xml'))

        # without elevation data
        cmd = [
            "netconvert",
            f'--node-files={path_node}',
            f'--edge-files={path_edge}',
            f'--output-file={path_net}',
            "--roundabouts.guess",
            "--ramps.guess",
            "--tls.discard-simple",
            "--tls.join",
            "--proj.utm",
            "--ignore-errors.edge-type",
        ]
        # command1 = f'cmd/c "netconvert --node-files={path_node} --edge-files={path_edge}\
        # --output-file={path_net} --roundabouts.guess --ramps.guess\
        # --tls.discard-simple --tls.join --proj.utm --ignore-errors.edge-type"'
        # os.system(command1)

        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        # print("Return code:", result.returncode)
        # print("STDOUT:\n", result.stdout)
        # print("STDERR:\n", result.stderr)

        # change back to current directory
        os.chdir(current_dir)

    except Exception as e:
        warnings.warn(f"  :Error in creating SUMO network: {e}")
        return False

    return True


def create_opendrive_xodr_from_sumo_net(net_name: str, net_dir: str) -> bool:
    """Create OpenDrive xodr file from SUMO Network using netconvert.

    Args:
        net_name (str): The name of the network.
        net_dir (str): The directory include sub-directory 'OpenDrive', where the SUMO network file is located.

    Note:
        This function will load sub-directory 'OpenDrive' in the net_dir to find the SUMO network file.

    Returns:
        bool: True if the OpenDrive network is created successfully, False otherwise.
    """

    try:
        # get sumo net path
        path_opendrive_net = pf.path2linux(os.path.join(net_dir, f'OpenDrive/{net_name}.net.xml'))
        path_opendrive_xodr = pf.path2linux(os.path.join(net_dir, f'OpenDrive/{net_name}.xodr'))

        if not os.path.exists(net_dir):
            os.makedirs(net_dir, exist_ok=True)

        if not os.path.exists(Path(net_dir) / 'OpenDrive'):
            os.makedirs(Path(net_dir) / 'OpenDrive', exist_ok=True)

        # command2 = f'cmd/c "netconvert -s {path_opendrive_net} --opendrive-output={path_opendrive_xodr}"'
        # os.system(command2)

        cmd = [
            "netconvert",
            f"-s {path_opendrive_net}",
            f"--opendrive-output={path_opendrive_xodr}",
        ]
        subprocess.run(cmd, capture_output=True, text=True, shell=False)
        # print("Return code:", result.returncode)
        # print("STDOUT:\n", result.stdout)
        # print("STDERR:\n", result.stderr)

    except Exception as e:
        warnings.warn(f"  :Error in creating OpenDrive xodr: {e}")
        return False

    return True


class OpenDriveNetwork:
    """The OpenDriveNetwork class to generate OpenDrive network"""
    def __init__(self,
                 net_name: str = "network",
                 net_vertices: str = "",
                 ele_map: str = "No elevation map provided!",
                 output_dir: str = "output"):

        self._net_name = net_name
        self._net_vertices = net_vertices
        self._ele_map = ele_map

        self._output_dir = output_dir
        self.OpenDrive_network = []

        # create output directory
        # path_openDrive = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive'))
        # if not os.path.exists(self._output_dir):
        #     os.makedirs(self._output_dir, exist_ok=True)
        # # Create OpenDrive directory
        # if os.path.exists(path_openDrive):
        #     # Delete existing directory and its contents
        #     shutil.rmtree(path_openDrive)
        # # Create new directory
        # os.makedirs(path_openDrive, exist_ok=True)

    def isEmpty(self):
        """Check if the OpenDriveNetwork element is empty"""
        pass

    def setValue(self):
        """Create OpenDrive network and save it to the output directory"""

        path_openDrive = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive'))

        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir, exist_ok=True)

        if os.path.exists(path_openDrive):
            # Delete existing directory and its contents
            shutil.rmtree(path_openDrive)

        # Create new directory
        os.makedirs(path_openDrive, exist_ok=True)

        self.create_SUMO_network()
        self.create_OpenDrive_network()

    def create_OpenDrive_network(self):
        """Create OpenDrive network from SUMO Network"""
        # get node and edge path
        path_net = pf.path2linux(os.path.join(self._output_dir, f'OpenDrive/{self._net_name}.net.xml'))
        path_net_elevation = pf.path2linux(
            os.path.join(self._output_dir, f'OpenDrive/{self._net_name}_WithElevation.net.xml'))
        path_open_drive_ele = pf.path2linux(
            os.path.join(self._output_dir, f'OpenDrive/{self._net_name}_WithElevation.xodr'))
        path_open_drive_output = pf.path2linux(
            os.path.join(self._output_dir, f'OpenDrive/{self._net_name}.xodr'))

        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir, exist_ok=True)

        if not os.path.exists(Path(self._output_dir) / 'OpenDrive'):
            os.makedirs(Path(self._output_dir) / 'OpenDrive', exist_ok=True)

        command2 = f'cmd/c "netconvert -s {path_net} --opendrive-output={path_open_drive_output}"'
        os.system(command2)
        self.OpenDrive_network = [path_open_drive_output]

        # with elevation data
        if self._ele_map != "No elevation map provided!":
            command4 = f'cmd/c "netconvert -s {path_net_elevation} --opendrive-output={path_open_drive_ele}"'
            os.system(command4)
            self.OpenDrive_network.append(path_open_drive_ele)
        else:
            self.OpenDrive_network.append(None)

    def create_SUMO_network(self):
        """Generate OpenDrive network from OpenStreetMap"""

        path_openDrive = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive'))

        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir, exist_ok=True)

        if os.path.exists(path_openDrive):
            # Delete existing directory and its contents
            shutil.rmtree(path_openDrive)

        # Create new directory
        os.makedirs(path_openDrive, exist_ok=True)

        # create networkx graph network
        nx_net = OSMRoad(output_dir=self._output_dir)
        nx_net.get_graph(self._net_vertices)
        nx_net.add_spread()
        nx_net.add_num_lane()
        nx_net.add_missing_value()
        nx_net.generate_edges()
        nx_net.generate_nodes()

        # get node and edge path
        path_node = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive/nodes.nod.xml'))
        path_edge = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive/edges.edg.xml'))
        path_net = pf.path2linux(os.path.join(self._output_dir, f'OpenDrive/{self._net_name}.net.xml'))
        path_net_elevation = pf.path2linux(
            os.path.join(self._output_dir, f'OpenDrive/{self._net_name}_WithElevation.net.xml'))

        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir, exist_ok=True)

        if not os.path.exists(Path(self._output_dir) / 'OpenDrive'):
            os.makedirs(Path(self._output_dir) / 'OpenDrive', exist_ok=True)

        # without elevation data
        command1 = f'cmd/c "netconvert --node-files={path_node} --edge-files={path_edge}\
        --output-file={path_net} --roundabouts.guess --ramps.guess\
        --tls.discard-simple --tls.join --proj.utm --ignore-errors.edge-type"'

        # command2 = f'cmd/c "netconvert -s {path_net} --opendrive-output={path_open_drive_output}"'

        os.system(command1)
        # os.system(command2)
        # self.OpenDrive_network = [path_open_drive_output]

        # with elevation data
        if self._ele_map != "No elevation map provided!":
            command3 = f'cmd/c "netconvert --node-files={path_node} --edge-files={path_edge}\
            --output-file={path_net_elevation} --roundabouts.guess --ramps.guess\
            --tls.discard-simple --tls.join --heightmap.geotiff {self._net_name}.tif --proj.utm"'

            # command4 = f'cmd/c "netconvert -s {path_net_elevation} --opendrive-output={path_open_drive_ele}"'

            os.system(command3)
            # os.system(command4)
            # self.OpenDrive_network.append(path_open_drive_ele)
        else:
            # self.OpenDrive_network.append(None)
            pass


class OSMRoad:
    """The OSMRoad class to generate network from OpenStreetMap"""

    def __init__(self, output_dir : str = "RT_Network"):

        self._output_dir = output_dir
        self.G = nx.empty_graph()

    def get_graph(self, NetworkVertices):
        """Get the graph from OpenStreetMap using osmnx"""

        if isinstance(NetworkVertices, str):

            # NetworkVertices = " (-85.14985634615098, 35.0401442512819), ( -85.15827848213861, 35.04329333848216),
            # (-85.15818728703556,35.04347780007786), (-85.14975978663011,35.04037264104675)"

            NetworkVerticesTemp = NetworkVertices.replace(' ', '').split('),(')
            NetworkVerticesTemp[0] = NetworkVerticesTemp[0][1:]
            NetworkVerticesTemp[-1] = NetworkVerticesTemp[-1][:-1]
            NetworkVerticesList = [tuple((float(ele) for ele in tup.split(',')))
                                   for tup in NetworkVerticesTemp]
        elif isinstance(NetworkVertices, list):
            # Check if the list contains tuples
            if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in NetworkVertices):
                NetworkVerticesList = [(float(item[0]), float(item[1])) for item in NetworkVertices]
            else:
                raise ValueError("Invalid format: List must contain list of [lon, lat].")

        polygon = Polygon(NetworkVerticesList)
        self.G = ox.graph.graph_from_polygon(
            polygon, network_type='drive_service', simplify=True, truncate_by_edge=True)
        self.G = ox.add_edge_speeds(self.G)
        self.G = ox.add_edge_travel_times(self.G)

        self.G.remove_edges_from(nx.selfloop_edges(self.G))

        nodes, edges = ox.graph_to_gdfs(self.G, fill_edge_geometry=True)

        self.G = ox.graph_from_gdfs(nodes, edges, graph_attrs=self.G.graph)
        # ox.plot_graph(self.G)

    def line_str(self, line):
        """Convert line to string"""

        for jx, j in enumerate(list(line.coords)):
            # s_x,s_y=net.convertLonLat2XY(j[0],j[1])
            if jx == 0:
                # s = '%s,%s' % (j[0], j[1])
                s = f"{j[0]},{j[1]}"
            else:
                # s = s + ' %s,%s' % (j[0], j[1])
                s += f" {j[0]},{j[1]}"
        return s

    def split_lane_no(self, str_digit):
        """Split the lane number"""
        float_digit = float(str_digit)
        return [math.ceil(float_digit / 2.0), math.floor(float_digit / 2.0)]

    def add_spread(self):
        """Add spread to the edges"""

        for _, _, d in self.G.edges(data=True):
            if 'lanes' in d:
                try:
                    # no_lanes = '%.0f' % (float(d['lanes']))
                    no_lanes = f"{float(d['lanes']):.0f}"
                except Exception:
                    # no_lanes = '%.0f' % (float(d['lanes'][0]))
                    no_lanes = f"{float(d['lanes'][0]):.0f}"

                if d['oneway']:
                    d['spread'] = 'center'
                    d['n_lane'] = no_lanes
                else:
                    if float(no_lanes) > 1 and float(no_lanes) % 2 == 0:
                        d['spread'] = 'right'
                        d['n_lane'] = self.split_lane_no(no_lanes)

                    elif float(no_lanes) > 1 and float(no_lanes) % 2 == 0:
                        d['spread'] = 'roadCenter'
                        d['n_lane'] = self.split_lane_no(no_lanes)

    def add_num_lane(self):
        """Add number of lanes to the edges"""
        for e1, e2, d in self.G.edges(data=True):
            if 'n_lane' in d:
                if d['oneway'] is False and isinstance(d['n_lane'], list) is True:
                    k = list(self.G[e2][e1].items())[0][0]
                    self.G[e2][e1][k]['n_lane'] = f'{float(d["n_lane"][-1]):.0f}'

                    # d['n_lane'] = '%.0f' % (float(d['n_lane'][0]))
                    d["n_lane"] = f"{float(d['n_lane'][0]):.0f}"

    def add_missing_value(self):
        """Add missing values to the edges"""
        for e1, e2, d in self.G.edges(data=True):
            # d['u_id'] = '%s%s' % (e1, e2)
            d["u_id"] = f"{e1}{e2}"

            if 'n_lane' not in d:
                d['n_lane'] = ' '

            if 'spread' not in d:
                if d['oneway']:
                    d['spread'] = 'center'
                else:
                    d['spread'] = 'right'

    def generate_edges(self):
        """Generate edges from the graph"""
        edges = []
        for e1, e2, d in self.G.edges(data=True):
            edges.append([d['u_id'], e1, e2, f'{d["n_lane"]}',
                          self.line_str(d['geometry']), float(
                              d['speed_kph']) * 0.28 + 2.22,
                          d['spread']])

        df_edge = pd.DataFrame(edges)

        df_edge.columns = ['id', 'from', 'to', 'numLanes', 'shape', 'speed', 'spreadType']
        for i in df_edge.index:
            if df_edge['numLanes'][i] == ' ':
                df_edge.at[i, 'numLanes'] = np.nan

        # df_edge=df_edge.fillna(np.nan)
        # print(df_edge.head())

        path_edge = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive/edges.edg.xml'))
        df_edge.to_xml(path_edge,
                       attr_cols=['id', 'from', 'to', 'numLanes',
                                  'shape', 'speed', 'spreadType'],
                       root_name='edges',
                       row_name='edge',
                       index=False)

    def generate_nodes(self):
        """Generate nodes from the graph"""

        nodes = []
        for n, d in self.G.nodes(data=True):
            nodes.append([n, d['x'], d['y'], 'priority'])
            try:
                if d['highway'] == 'traffic_signals':
                    nodes.append([n, d['x'], d['y'], 'traffic_light'])
            except Exception:
                continue

        df_node = pd.DataFrame(nodes)
        df_node.columns = ['id', 'x', 'y', 'type']

        path_node = pf.path2linux(os.path.join(self._output_dir, 'OpenDrive/nodes.nod.xml'))
        df_node.to_xml(path_node,
                       attr_cols=['id', 'x', 'y', 'type'],
                       root_name='nodes',
                       row_name='node',
                       index=False)
