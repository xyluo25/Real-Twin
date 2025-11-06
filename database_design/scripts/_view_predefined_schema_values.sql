-- save these schema values in db
@set lanee = ('road_class', 'lane_type', 'node_type', 'signal_control_type', 'phase_type', 'veh_type')

SELECT t.typname, e.enumlabel AS value, e.enumsortorder
FROM pg_type t
JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' AND t.typname in ${lanee}
ORDER BY t.typname, e.enumsortorder;