-- 2) Drop in reverse dependency order

-- Demand first
DROP TABLE IF EXISTS demand.vehicle_trip CASCADE;
DROP TABLE IF EXISTS demand.path CASCADE;
DROP TABLE IF EXISTS demand.turning_flow CASCADE;
DROP TABLE IF EXISTS demand.od_entry CASCADE;
DROP TABLE IF EXISTS demand.od_matrix CASCADE;
DROP TABLE IF EXISTS demand.centroid_connector CASCADE;
DROP TABLE IF EXISTS demand.zone CASCADE;

-- traffic signals next
DROP TABLE IF EXISTS signal.timing_plan_phase CASCADE;
DROP TABLE IF EXISTS signal.timing_plan CASCADE;
DROP TABLE IF EXISTS signal.detector CASCADE;
DROP TABLE IF EXISTS signal.phase_movement CASCADE;
DROP TABLE IF EXISTS signal.phase CASCADE;
DROP TABLE IF EXISTS signal.controller CASCADE;

-- Geometry last
DROP TABLE IF EXISTS network.movement CASCADE;
DROP TABLE IF EXISTS network.lane CASCADE;
DROP TABLE IF EXISTS network.link CASCADE;
DROP TABLE IF EXISTS network.node CASCADE;
