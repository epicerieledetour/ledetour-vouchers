CREATE VIEW IF NOT EXISTS
users
AS
SELECT
    elemid as id,
    MAX(distinct case when field = 'label' then value end) as label,
    MAX(distinct case when field = 'description' then value end) as description,
    MAX(distinct case when field = 'deleted' then value end) as deleted
FROM elems
GROUP BY elemid
ORDER BY label