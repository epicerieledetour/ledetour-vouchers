SELECT
	emission_contents.sortnumber AS voucher_sortnumber,
	vouchers.value_CAD AS voucher_value_CAD,
	users.label AS distributor_label
FROM emission_contents
JOIN vouchers ON emission_contents.voucherid = vouchers.id
JOIN users ON vouchers.distributed_by = users.id
WHERE emissionid = :emissionid
ORDER BY emission_contents.sortnumber