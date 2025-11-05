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

"""The module to prepare the simulation from the concrete scenario."""

# import four elements of AbstractScenario
from ._sumo import SUMOPrep
from ._aimsun import AimsunPrep
from ._vissim import VissimPrep


class SimPrep:
    '''Prepare simulation from concrete scenario'''

    def __init__(self, **kwargs):
        self.SUMOSim = SUMOPrep(**kwargs)
        self.AimsunSim = AimsunPrep(**kwargs)
        self.VissimSim = VissimPrep(**kwargs)

    def create_sumo_sim(self,
                        input_config: dict,
                        start_time: float = 3600 * 8,
                        end_time: float = 3600 * 10,
                        seed: list | int = 812,
                        step_length: float = 0.1) -> bool:
        """Prepare SUMO documents for simulation.

        Args:
            input_config (dict): The input configuration dictionary.
            start_time (float): The simulation start time in seconds. Default is 8 AM (3600 * 8).
            end_time (float): The simulation end time in seconds. Default is 10 AM (3600 * 10).
            seed (list | int): The random seed(s) for the simulation. Default is 812.
            step_length (float): The simulation step length in seconds. Default is 0.1 seconds.
        Returns:
            bool: True if the SUMO simulation preparation is successful, False otherwise.
        """

        # check seed type
        if isinstance(seed, int):
            seed = [seed]
        elif isinstance(seed, list):
            pass
        else:
            raise ValueError("  :seed must be an integer or a list of integers.")
        if len(seed) > 1:
            print("  :Multiple seeds are provided, the first one will be used.")
            seed = seed[0]

        self.SUMOSim.importNetwork(input_config)
        self.SUMOSim.importDemand(input_config,
                                  start_time,
                                  end_time,
                                  seed)
        self.SUMOSim.generateConfig(input_config,
                                    start_time,
                                    end_time,
                                    seed,
                                    step_length)
        self.SUMOSim.importSignal(input_config)
        # print("  :SUMO simulation is prepared.")

    def create_aimsun_sim(self,
                          input_config,
                          start_time: float = 3600 * 8,
                          end_time: float = 3600 * 10,
                          seed: list | int = 812,
                          step_length: float = 0.1):
        """Prepare Aimsun documents for simulation."""
        # self.AimsunSim.importDemand(input_config, start_time, end_time)

    def create_vissim_sim(self,
                          input_config,
                          start_time: float = 3600 * 8,
                          end_time: float = 3600 * 10,
                          seed: list | int = 812,
                          step_length: float = 0.1):
        """Prepare VISSIM documents for simulation."""

        print("  :VISSIM simulation preparation is not implemented yet.")
        self.VissimSim.verbose = True
