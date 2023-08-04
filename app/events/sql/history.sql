SELECT *
FROM events
WHERE elemid IN ({ids_string})
ORDER BY
    elemid;
--     timestamp_utc DESC;