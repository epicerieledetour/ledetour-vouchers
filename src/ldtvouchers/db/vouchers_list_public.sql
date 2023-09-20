SELECT *
FROM vouchers, tokens
ON vouchers.voucherid = tokens.idintable AND tokens.tablename = "vouchers"
WHERE emissionid = :emissionid;