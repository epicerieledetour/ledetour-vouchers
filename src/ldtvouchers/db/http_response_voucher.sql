SELECT
	a.req_vouchertoken AS token,
	v.value_CAN AS value_CAN,
	e.expiration_utc AS expiration_utc,
	u.label AS cashedin_by_label,
	u.description AS cashedin_by_description,
	v.cashedin_utc AS cashedin_utc,
	r.can_undo AS can_undo,
	v.undo_expiration_utc AS undo_expiration_utc
FROM actions a, responses r, users u, vouchers v, emissions e
ON
	v.voucherid = a.voucherid
	AND e.emissionid = v.emissionid
	AND u.userid = COALESCE(v.cashedin_by, a.userid)
	AND r.responseid = a.responseid
WHERE a.actionid = :actionid;