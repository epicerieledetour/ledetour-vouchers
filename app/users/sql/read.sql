SELECT *
FROM users
WHERE id IN ({ids_string})
AND deleted = '0'