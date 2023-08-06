SELECT *
FROM emissions
WHERE id IN ({ids_string})
AND deleted = '0'