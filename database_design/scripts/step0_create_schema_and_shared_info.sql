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
    'through', 'left', 'right', 'u_turn',
    'through_right', 'through_left', 'through_right_left',
    'bus', 'bike', 'parking', 'shoulder', 'aux'
);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_mode') THEN CREATE TYPE access_mode AS ENUM(
    'all', 'car', 'truck', 'bus', 'bike', 'ped');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signal_control_type') THEN CREATE TYPE signal_control_type AS ENUM(
    'fixed_time', 'actuated', 'adaptive');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN CREATE TYPE phase_type AS ENUM(
    'permitted', 'protected', 'flashing');
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN CREATE TYPE phase_type AS ENUM(
    'permitted', 'protected', 'flashing');
END IF;

END $$;
