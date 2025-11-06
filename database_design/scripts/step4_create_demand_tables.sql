-- 5) Demand schema

-- Turning movement demand tied to geometric movements
CREATE TABLE demand.turning_flow (
    turn_flow_id BIGSERIAL PRIMARY KEY,
    link_id_from BIGINT NOT NULL REFERENCES network.link (link_id) ON DELETE CASCADE,
    link_id_to BIGINT NOT NULL REFERENCES network.link (link_id) ON DELETE CASCADE,
    veh_type veh_type DEFAULT 'car',
    flow DOUBLE PRECISION -- optional vehicles in slice or rate
);
CREATE INDEX IF NOT EXISTS idx_turn_from_to ON demand.turning_flow (link_id_from, link_id_to);

-- path
CREATE TABLE demand.route (
  route_id        BIGSERIAL PRIMARY KEY,
  node_id_from BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE CASCADE,
  node_id_to BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE CASCADE,
  link_seq       BIGINT[],  -- ordered network.link ids
  geom  GEOMETRY (LINESTRING, 4326) -- path geometry
);


-- OD data
CREATE TABLE demand.origin_destination (
    od_id BIGSERIAL PRIMARY KEY,
    node_id_from BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE CASCADE,
    node_id_to BIGINT NOT NULL REFERENCES network.node (node_id) ON DELETE CASCADE,
    veh_type veh_type DEFAULT 'car',
    flow DOUBLE PRECISION, -- optional vehicles in slice or rate
    date DATE NOT NULL,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Sunday, 6=Saturday
    date_type TEXT CHECK (date_type IN ('weekday', 'weekend')) DEFAULT 'weekday',
    time_from TIMESTAMP,      -- in HH:MM format
    time_to TIMESTAMP      -- in HH:MM format
);

-- vehicle trips
CREATE TABLE demand.vehicle_trip (
    trip_id BIGSERIAL PRIMARY KEY,
    route_id BIGINT REFERENCES demand.route (route_id),
    od_id BIGINT REFERENCES demand.origin_destination (od_id),
    depart_time TIMESTAMP NOT NULL,
    veh_type veh_type DEFAULT 'car'
);

COMMIT;