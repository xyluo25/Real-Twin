-- 3) Geometry schema: node, link, lane, movement

-- Node types from OSM: https://wiki.openstreetmap.org/wiki/Map_features
CREATE TABLE network.node (
    node_id BIGSERIAL PRIMARY KEY,
    node_type node_type DEFAULT NULL, -- intersection, signal, centroid, etc.
    lon DOUBLE PRECISION NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    srid INTEGER DEFAULT 4326,
    geom geometry (Point, 4326) GENERATED ALWAYS AS (ST_SetSRID (ST_MakePoint (lon, lat), COALESCE(srid, 4326))) STORED
);

CREATE INDEX IF NOT EXISTS idx_node_geom ON network.node USING GIST (geom);

-- add column comments for clarity
COMMENT ON COLUMN network.node.node_id IS 'Unique identifier for each node in the network';
COMMENT ON COLUMN network.node.node_type IS 'Type of node, e.g., intersection, signal, centroid, etc.';
COMMENT ON COLUMN network.node.x IS 'X coordinate of the node in the specified SRID';
COMMENT ON COLUMN network.node.y IS 'Y coordinate of the node in the specified SRID';
COMMENT ON COLUMN network.node.srid IS 'Spatial Reference System Identifier for the node coordinates';
COMMENT ON COLUMN network.node.geom IS 'Geometry of the node as a Point in the specified SRID';

CREATE TABLE network.link (
    link_id BIGSERIAL PRIMARY KEY,
    node_id_from BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE RESTRICT,
    node_id_to BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE RESTRICT,
    road_name TEXT,
    road_class road_class DEFAULT 'motorway',
    length DOUBLE PRECISION,
    free_speed DOUBLE PRECISION,
    capacity INTEGER,
    lanes_count INTEGER CHECK (lanes_count >= 0),
    grade_percent DOUBLE PRECISION,
    bearing DOUBLE PRECISION,  -- The bearing in degrees clockwise from true north
    priority_road BOOLEAN DEFAULT FALSE,
    geom geometry (LineString, 4326)
);

CREATE INDEX IF NOT EXISTS idx_link_geom ON network.link USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_link_from_to ON network.link (node_id_from, node_id_to);

COMMENT ON COLUMN network.link.link_id IS 'Unique identifier for each link in the network';
COMMENT ON COLUMN network.link.node_id_from IS 'Starting node of the link';
COMMENT ON COLUMN network.link.node_id_to IS 'Ending node of the link';
COMMENT ON COLUMN network.link.road_name IS 'Name of the road';
COMMENT ON COLUMN network.link.road_class IS 'Class of the road';
COMMENT ON COLUMN network.link.length IS 'Length of the link in meters';
COMMENT ON COLUMN network.link.free_speed IS 'Free flow speed on the link in km/h';
COMMENT ON COLUMN network.link.capacity IS 'Capacity of the link in vehicles per hour';
COMMENT ON COLUMN network.link.lanes_count IS 'Number of lanes on the link';
COMMENT ON COLUMN network.link.grade_percent IS 'Grade percentage of the link';
COMMENT ON COLUMN network.link.bearing IS 'Bearing of the link in degrees clockwise from true north';
COMMENT ON COLUMN network.link.geom IS 'Geometry of the link as a LineString in SRID 4326';


CREATE TABLE network.lane (
  lane_id        BIGSERIAL PRIMARY KEY,
  link_id        BIGINT NOT NULL REFERENCES network.link(link_id) ON DELETE CASCADE,
  lane_index     INTEGER NOT NULL,  -- 1 = leftmost, increase to right?
  lane_type      lane_type DEFAULT NULL,
  width          DOUBLE PRECISION,
  speed          DOUBLE PRECISION,
  is_hov         BOOLEAN DEFAULT FALSE,
  is_reversible  BOOLEAN DEFAULT FALSE,
  geom           geometry (LineString, 4326),
  UNIQUE (link_id, lane_index)
);
CREATE INDEX IF NOT EXISTS idx_lane_link ON network.lane (link_id);

COMMENT ON COLUMN network.lane.lane_id IS 'Unique identifier for each lane';
COMMENT ON COLUMN network.lane.link_id IS 'Identifier of the link this lane belongs to';
COMMENT ON COLUMN network.lane.lane_index IS 'Index of the lane within the link';
COMMENT ON COLUMN network.lane.lane_type IS 'Type of the lane, e.g., driving, turning, shoulder, etc.';
COMMENT ON COLUMN network.lane.width IS 'Width of the lane in meters';
COMMENT ON COLUMN network.lane.speed IS 'Speed limit of the lane in km/h';
COMMENT ON COLUMN network.lane.is_hov IS 'Indicates if the lane is for HOV (High Occupancy Vehicle) use';
COMMENT ON COLUMN network.lane.is_reversible IS 'Indicates if the lane is reversible';
COMMENT ON COLUMN network.lane.geom IS 'Geometry of the lane as a LineString in SRID 4326';


CREATE TABLE network.movement (
    movement_id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE CASCADE,
    link_id_from BIGINT NOT NULL REFERENCES network.link (link_id) ON DELETE CASCADE,
    link_id_to BIGINT NOT NULL REFERENCES network.link (link_id) ON DELETE CASCADE,
    lane_id_from BIGINT REFERENCES network.lane (lane_id) ON DELETE SET NULL,
    lane_id_to BIGINT REFERENCES network.lane (lane_id) ON DELETE SET NULL,
    turn_type lane_type DEFAULT NULL -- left, through, right, u_turn
);

CREATE INDEX IF NOT EXISTS idx_mvmt ON network.movement (node_id);
CREATE INDEX IF NOT EXISTS idx_mvmt_from_to ON network.movement (link_id_from, link_id_to);

COMMENT ON COLUMN network.movement.movement_id IS 'Unique identifier for each movement';
COMMENT ON COLUMN network.movement.node_id IS 'Node where the movement occurs';
COMMENT ON COLUMN network.movement.link_id_from IS 'Link from which the movement originates';
COMMENT ON COLUMN network.movement.link_id_to IS 'Link to which the movement goes';
COMMENT ON COLUMN network.movement.lane_id_from IS 'Lane from which the movement originates';
COMMENT ON COLUMN network.movement.lane_id_to IS 'Lane to which the movement goes';
COMMENT ON COLUMN network.movement.turn_type IS 'Type of turn for the movement, e.g., left, through, right, u_turn';

-- zone table
CREATE TABLE demand.zone (
    zone_id BIGSERIAL PRIMARY KEY,
    zone_name TEXT,
    geom geometry (Polygon, 4326)
);
COMMENT ON COLUMN demand.zone.zone_id IS 'Unique identifier for each zone';
COMMENT ON COLUMN demand.zone.zone_name IS 'Name of the zone';
COMMENT ON COLUMN demand.zone.geom IS 'Geometry of the zone as a Polygon in SRID 4326';

-- Helper function to auto set link length from geometry
DROP TRIGGER IF EXISTS trg_set_link_length ON network.link;
DROP FUNCTION IF EXISTS network.set_link_length();

CREATE OR REPLACE FUNCTION network.set_link_length() RETURNS trigger AS $$
BEGIN
  IF NEW.geom IS NOT NULL THEN
    NEW.length := ST_Length(ST_Transform(NEW.geom, 3857));
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_link_length
BEFORE INSERT OR UPDATE ON network.link
FOR EACH ROW EXECUTE FUNCTION network.set_link_length();