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
