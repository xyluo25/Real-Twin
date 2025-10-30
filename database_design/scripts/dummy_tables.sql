BEGIN;

-- 0) Extensions and schemas
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS net;  -- geometry: node, link, lane, movement
CREATE SCHEMA IF NOT EXISTS sig;  -- signals
CREATE SCHEMA IF NOT EXISTS demand;  -- demand

-- 1) Shared types
DO $$
BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'road_class') THEN
    CREATE TYPE road_class AS ENUM ('motorway','primary','secondary','tertiary','residential','service','ramp','other');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lane_type') THEN CREATE TYPE lane_type AS ENUM(
    'through',
    'left',
    'right',
    'u_turn',
    'through_right',
    'through_left',
    'through_right_left',
    'bus',
    'bike',
    'parking',
    'shoulder',
    'aux'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_mode') THEN CREATE TYPE access_mode AS ENUM(
    'all',
    'car',
    'truck',
    'bus',
    'bike',
    'ped'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signal_control_type') THEN CREATE TYPE signal_control_type AS ENUM(
    'fixed_time',
    'actuated',
    'adaptive'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN CREATE TYPE phase_type AS ENUM(
    'permitted',
    'protected',
    'flashing'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN CREATE TYPE phase_type AS ENUM(
    'permitted',
    'protected',
    'flashing'
);
END IF;

END $$;

-- 2) Drop in reverse dependency order

-- Demand first
DROP TABLE IF EXISTS demand.vehicle_trip CASCADE;
DROP TABLE IF EXISTS demand.path CASCADE;
DROP TABLE IF EXISTS demand.turning_flow CASCADE;
DROP TABLE IF EXISTS demand.od_entry CASCADE;
DROP TABLE IF EXISTS demand.od_matrix CASCADE;
DROP TABLE IF EXISTS demand.centroid_connector CASCADE;
DROP TABLE IF EXISTS demand.zone CASCADE;

-- Signals next
DROP TABLE IF EXISTS sig.timing_plan_phase CASCADE;
DROP TABLE IF EXISTS sig.timing_plan CASCADE;
DROP TABLE IF EXISTS sig.detector CASCADE;
DROP TABLE IF EXISTS sig.phase_movement CASCADE;
DROP TABLE IF EXISTS sig.signal_phase CASCADE;
DROP TABLE IF EXISTS sig.signal_controller CASCADE;

-- Geometry last
DROP TABLE IF EXISTS net.movement CASCADE;
DROP TABLE IF EXISTS net.lane CASCADE;
DROP TABLE IF EXISTS net.link CASCADE;
DROP TABLE IF EXISTS net.node CASCADE;

-- 3) Geometry schema: node, link, lane, movement

CREATE TABLE net.node (
    node_id BIGSERIAL PRIMARY KEY,
    node_type TEXT, -- intersection, centroid, stop_bar, etc.
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    srid INTEGER DEFAULT 4326,
    -- elevation_m DOUBLE PRECISION,
    -- is_signalized BOOLEAN DEFAULT FALSE,
    geom geometry (Point, 4326) GENERATED ALWAYS AS (
        ST_SetSRID (
            ST_MakePoint (x, y),
            COALESCE(srid, 4326)
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_node_geom ON net.node USING GIST (geom);

CREATE TABLE net.link (
    link_id BIGSERIAL PRIMARY KEY,
    from_node_id BIGINT NOT NULL REFERENCES net.node (node_id) ON DELETE RESTRICT,
    to_node_id BIGINT NOT NULL REFERENCES net.node (node_id) ON DELETE RESTRICT,
    road_name TEXT,
    road_class road_class DEFAULT 'other',
    length_m DOUBLE PRECISION,
    free_speed_kph DOUBLE PRECISION,
    capacity_vph INTEGER,
    lanes_count INTEGER CHECK (lanes_count >= 0),
    access access_mode DEFAULT 'all',
    is_one_way BOOLEAN DEFAULT TRUE,
    grade_percent DOUBLE PRECISION,
    toll BOOLEAN DEFAULT FALSE,
    geom geometry (LineString, 4326)
);

CREATE INDEX IF NOT EXISTS idx_link_geom ON net.link USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_link_from_to ON net.link (from_node_id, to_node_id);

CREATE TABLE net.lane (
  lane_id        BIGSERIAL PRIMARY KEY,
  link_id        BIGINT NOT NULL REFERENCES net.link(link_id) ON DELETE CASCADE,
  lane_index     INTEGER NOT NULL,              -- 1 = leftmost, increase to right
  lane_type      lane_type DEFAULT 'through',
  width_m        DOUBLE PRECISION,
  allowed_modes  access_mode[] DEFAULT ARRAY['all']::access_mode[],
  speed_kph      DOUBLE PRECISION,
  is_hov         BOOLEAN DEFAULT FALSE,
  is_reversible  BOOLEAN DEFAULT FALSE,
  UNIQUE (link_id, lane_index)
);

CREATE INDEX IF NOT EXISTS idx_lane_link ON net.lane (link_id);

CREATE TABLE net.movement (
    movement_id BIGSERIAL PRIMARY KEY,
    via_node_id BIGINT NOT NULL REFERENCES net.node (node_id) ON DELETE CASCADE,
    from_link_id BIGINT NOT NULL REFERENCES net.link (link_id) ON DELETE CASCADE,
    to_link_id BIGINT NOT NULL REFERENCES net.link (link_id) ON DELETE CASCADE,
    from_lane_id BIGINT REFERENCES net.lane (lane_id) ON DELETE SET NULL,
    to_lane_id BIGINT REFERENCES net.lane (lane_id) ON DELETE SET NULL,
    turn_type lane_type, -- left, through, right, u_turn
    is_allowed BOOLEAN DEFAULT TRUE,
    cost_penalty_s DOUBLE PRECISION,
    UNIQUE (
        via_node_id,
        from_link_id,
        to_link_id,
        COALESCE(from_lane_id, 0),
        COALESCE(to_lane_id, 0)
    )
);

CREATE INDEX IF NOT EXISTS idx_mvmt_via ON net.movement (via_node_id);

CREATE INDEX IF NOT EXISTS idx_mvmt_from_to ON net.movement (from_link_id, to_link_id);

-- Helper function to auto set link length from geometry
DROP TRIGGER IF EXISTS trg_set_link_length ON net.link;
DROP FUNCTION IF EXISTS net.set_link_length();

CREATE OR REPLACE FUNCTION net.set_link_length() RETURNS trigger AS $$
BEGIN
  IF NEW.geom IS NOT NULL THEN
    NEW.length_m := ST_Length(ST_Transform(NEW.geom, 3857));
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_link_length
BEFORE INSERT OR UPDATE ON net.link
FOR EACH ROW EXECUTE FUNCTION net.set_link_length();

-- 4) Signal schema

CREATE TABLE sig.signal_controller (
    controller_id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL UNIQUE REFERENCES net.node (node_id) ON DELETE CASCADE,
    control_type signal_control_type NOT NULL,
    cycle_length_s INTEGER,
    offset_s INTEGER DEFAULT 0,
    description TEXT
);

CREATE TABLE sig.signal_phase (
    phase_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES sig.signal_controller (controller_id) ON DELETE CASCADE,
    phase_no INTEGER NOT NULL,
    phase_type phase_type NOT NULL,
    green_s INTEGER NOT NULL CHECK (green_s >= 0),
    yellow_s INTEGER NOT NULL CHECK (yellow_s >= 0),
    all_red_s INTEGER NOT NULL CHECK (all_red_s >= 0),
    UNIQUE (controller_id, phase_no)
);

CREATE TABLE sig.phase_movement (
    phase_id BIGINT NOT NULL REFERENCES sig.signal_phase (phase_id) ON DELETE CASCADE,
    --  movement_id    BIGINT NOT NULL REFERENCES net.movement(movement_id) ON DELETE CASCADE,
    is_protected BOOLEAN DEFAULT TRUE,
    --  PRIMARY KEY (phase_id, movement_id)
    PRIMARY KEY (phase_id)
);

CREATE TABLE sig.detector (
    detector_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES sig.signal_controller (controller_id) ON DELETE CASCADE,
    --  movement_id    BIGINT REFERENCES net.movement(movement_id) ON DELETE SET NULL,
    link_id BIGINT REFERENCES net.link (link_id) ON DELETE SET NULL,
    lane_id BIGINT REFERENCES net.lane (lane_id) ON DELETE SET NULL,
    location_m DOUBLE PRECISION,
    detection_type TEXT
);

CREATE TABLE sig.timing_plan (
    plan_id BIGSERIAL PRIMARY KEY,
    controller_id BIGINT NOT NULL REFERENCES sig.signal_controller (controller_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    active_from TIME,
    active_to TIME,
    dow_mask BIT(7) DEFAULT B'1111111'
);

CREATE TABLE sig.timing_plan_phase (
    plan_id BIGINT NOT NULL REFERENCES sig.timing_plan (plan_id) ON DELETE CASCADE,
    phase_id BIGINT NOT NULL REFERENCES sig.signal_phase (phase_id) ON DELETE CASCADE,
    green_s INTEGER,
    yellow_s INTEGER,
    all_red_s INTEGER,
    sequence_no INTEGER,
    PRIMARY KEY (plan_id, phase_id)
);

-- 5) Demand schema

-- Zones store polygons for TAZ and optional centroids
CREATE TABLE demand.zone (
    zone_id BIGSERIAL PRIMARY KEY,
    ext_id TEXT UNIQUE,
    name TEXT,
    centroid_x DOUBLE PRECISION,
    centroid_y DOUBLE PRECISION,
    srid INTEGER DEFAULT 4326,
    geom geometry (Polygon, 4326)
);

CREATE INDEX IF NOT EXISTS idx_zone_geom ON demand.zone USING GIST (geom);

-- Connectors between zone and network
CREATE TABLE demand.centroid_connector (
    connector_id BIGSERIAL PRIMARY KEY,
    zone_id BIGINT NOT NULL REFERENCES demand.zone (zone_id) ON DELETE CASCADE,
    node_id BIGINT NOT NULL REFERENCES net.node (node_id) ON DELETE CASCADE,
    impedance_s DOUBLE PRECISION,
    UNIQUE (zone_id, node_id)
);

-- OD matrices and entries
CREATE TABLE demand.od_matrix (
    od_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    base_time TIMESTAMP,
    time_period_min INTEGER NOT NULL -- slice resolution
);

CREATE TABLE demand.od_entry (
    od_id BIGINT NOT NULL REFERENCES demand.od_matrix (od_id) ON DELETE CASCADE,
    slice_index INTEGER NOT NULL,
    o_zone_id BIGINT NOT NULL REFERENCES demand.zone (zone_id) ON DELETE CASCADE,
    d_zone_id BIGINT NOT NULL REFERENCES demand.zone (zone_id) ON DELETE CASCADE,
    demand_pcu DOUBLE PRECISION NOT NULL,
    mode access_mode DEFAULT 'car',
    PRIMARY KEY (
        od_id,
        slice_index,
        o_zone_id,
        d_zone_id,
        mode
    )
);

CREATE INDEX IF NOT EXISTS idx_odentry_lookup ON demand.od_entry (
    od_id,
    slice_index,
    o_zone_id,
    d_zone_id
);

-- Turning movement demand tied to geometric movements
-- Store by discrete slice or exact timestamp
CREATE TABLE demand.turning_flow (
  tf_id          BIGSERIAL PRIMARY KEY,
  movement_id    BIGINT NOT NULL REFERENCES net.movement(movement_id) ON DELETE CASCADE,
  time_slice     INTEGER,                        -- optional if using slices
  at_time        TIMESTAMP,                      -- optional if using timestamps
  volume_veh     DOUBLE PRECISION NOT NULL,      -- vehicles in slice or rate
  UNIQUE (movement_id, COALESCE(time_slice,-1), COALESCE(at_time, '0001-01-01'::timestamp))
);

CREATE INDEX IF NOT EXISTS idx_tf_movement ON demand.turning_flow (movement_id);

-- Optional path storage
CREATE TABLE demand.path (
  path_id        BIGSERIAL PRIMARY KEY,
  od_id          BIGINT REFERENCES demand.od_matrix(od_id) ON DELETE SET NULL,
  slice_index    INTEGER,
  o_zone_id      BIGINT REFERENCES demand.zone(zone_id) ON DELETE SET NULL,
  d_zone_id      BIGINT REFERENCES demand.zone(zone_id) ON DELETE SET NULL,
  link_seq       BIGINT[]                       -- ordered net.link ids
);

-- Optional vehicle trips
CREATE TABLE demand.vehicle_trip (
    trip_id BIGSERIAL PRIMARY KEY,
    depart_time TIMESTAMP NOT NULL,
    origin_zone_id BIGINT REFERENCES demand.zone (zone_id),
    dest_zone_id BIGINT REFERENCES demand.zone (zone_id),
    path_id BIGINT REFERENCES demand.path (path_id),
    vehicle_type TEXT DEFAULT 'car',
    value_of_time DOUBLE PRECISION
);

COMMIT;

-- 6) Useful examples

-- Insert a signalized node
-- INSERT INTO net.node (ext_id, x, y, is_signalized) VALUES ('N1', -84.3903, 35.0456, TRUE);

-- Build movements, bind them to phases, then load demand.turning_flow for time slices.

-- Nearest node query
-- SELECT node_id
-- FROM net.node
-- ORDER BY geom <-> ST_SetSRID(ST_MakePoint(-84.39, 35.046), 4326)
-- LIMIT 1;