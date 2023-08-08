CREATE VIEW IF NOT EXISTS
vouchers
AS
SELECT
    elemid as id,
    MAX(distinct case when field = 'deleted' then value end) as deleted,
    MAX(distinct case when field = 'value_CAD' then value end) as value_CAD,
    MAX(distinct case when field = 'status' then value end) as status
FROM elems
WHERE elemid LIKE 'voucher_%'
GROUP BY elemid;
