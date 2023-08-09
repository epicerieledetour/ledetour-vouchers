DROP VIEW IF EXISTS vouchers;

CREATE VIEW IF NOT EXISTS
vouchers
AS
SELECT
	elemid as id,
    MAX(distinct case when field = 'value_CAD' then value end) as value_CAD,
    MAX(distinct case when field = 'status' then value end) as status,
	MAX(distinct case when commandid = 'event_create' then userid end) as created_by,
	MAX(distinct case when commandid = 'event_create' then timestamp_utc end) as created_utc,
	MAX(distinct case when commandid = 'event_update' and field = 'status' and value = 'distributed' then userid end) as distributed_by,
	MAX(distinct case when commandid = 'event_update' and field = 'status' and value = 'distributed' then timestamp_utc end) as distributed_utc,
	MAX(distinct case when commandid = 'event_update' and field = 'status' and value = 'cashedin' then userid end) as cashedin_by,
	MAX(distinct case when commandid = 'event_update' and field = 'status' and value = 'cashedin' then timestamp_utc end) as cashedin_utc,
	MAX(distinct case when field = 'deleted' then value end) as deleted
FROM events
WHERE elemid LIKE 'voucher_%'
GROUP BY elemid;