SELECT
  c.relname AS table_name,
  a.attname AS column_name,
  pgd.description AS column_comment
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = a.attrelid AND pgd.objsubid = a.attnum
WHERE c.relname = 'node' AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum;