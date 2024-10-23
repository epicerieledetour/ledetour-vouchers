SELECT
    e.label AS emission,
    datetime(e.expiration_utc, "localtime") AS expiration_date,
	v.sortnumber AS sortnumber,
	t.token AS token,
	v.value_CAN AS value,
	COALESCE(ud.label, "") AS distributed_by_label,
	COALESCE(ud.description, "") AS distributed_by_description,
	datetime(v.cashedin_utc, "localtime") AS cashedin_date,
	COALESCE(uc.label, "") AS cashedin_by_label,
	COALESCE(uc.description, "") AS cashedin_by_description
FROM vouchers v
LEFT JOIN tokens t ON v.voucherid = t.idintable AND t.tablename = "vouchers"
LEFT JOIN users ud ON v.distributed_by = ud.userid
LEFT JOIN users uc ON v.cashedin_by = uc.userid
LEFT JOIN emissions e USING(emissionid)
ORDER BY e.expiration_utc DESC, e.label ASC, v.sortnumber ASC;