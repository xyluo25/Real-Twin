-- 0) Extensions and schemas
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS network;
-- geometry: node, link, lane, movement
CREATE SCHEMA IF NOT EXISTS signal;
-- signals
CREATE SCHEMA IF NOT EXISTS demand;
-- demand

-- 1) Shared types
DO $$
BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'road_class') THEN
    CREATE TYPE road_class AS ENUM ('motorway', 'primary', 'secondary', 'tertiary', 'residential', 'service', 'ramp', 'other');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lane_type') THEN CREATE TYPE lane_type AS ENUM(
    'through', 'left', 'right', 'u_turn',
    'through_right', 'through_left', 'through_right_left',
    'bus', 'bike', 'parking', 'shoulder', 'aux', 'all', 'car', 'truck', 'ped'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'node_type') THEN CREATE TYPE node_type AS ENUM(
    'intersection',  -- meaning un-signalized intersection
    'signal',
    'centroid',  -- POI centroid (for future use)
    'stop',  -- stop sign: all way stop, 2-way stop etc.
    'connector',  -- links centroids to the physical network
    'merge',   -- freeway on-ramp merge
    'diverge',   --Freeway off-ramp split
    'roundabout',
    'access_point',  -- Driveway, parking lot access, pickup/drop-off etc.
    'origin',  -- zone centroid for demand loading
    'destination',  -- zone centroid for demand loading
    'other');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signal_control_type') THEN CREATE TYPE signal_control_type AS ENUM(
    'fixed_time', 'actuated', 'adaptive');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN CREATE TYPE phase_type AS ENUM(
    'permitted', 'protected', 'flashing');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'veh_type') THEN CREATE TYPE veh_type AS ENUM(
    'car', 'truck', 'bus', 'EV', 'AV', 'bike', 'pedestrian', 'other');
END IF;

END $$;
