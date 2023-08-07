CREATE VIEW IF NOT EXISTS
emissions
AS
SELECT
    elemid as id,
    MAX(distinct case when field = 'label' then value end) as label,
    MAX(distinct case when field = 'description' then value end) as description,
    MAX(distinct case when field = 'deleted' then value end) as deleted,
    MAX(distinct case when field = 'expiration_utc' then value end) as expiration_utc
FROM elems
WHERE elemid LIKE 'emission_%'
GROUP BY elemid
ORDER BY expiration_utc