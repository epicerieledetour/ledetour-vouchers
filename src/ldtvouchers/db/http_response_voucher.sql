SELECT
	a.req_vouchertoken AS token,
	v.value_CAN AS value_CAN,
	u.label AS cashedin_by_label,
	u.description AS cashedin_by_description,
	v.cashedin_utc AS cashedin_utc,
	CASE
		WHEN r.can_undo
		THEN v.undo_expiration_utc
		ELSE NULL
	END AS undo_expiration_utc
FROM actions a, responses r, users u, vouchers v
ON
	v.voucherid = a.voucherid
	AND u.userid = v.cashedin_by
	AND r.responseid = a.responseid
WHERE a.actionid = :actionid;