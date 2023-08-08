SELECT *
FROM vouchers
WHERE id IN ({ids_string})
AND deleted = '0'