SELECT *, datetime(expiration_utc, "localtime") expiration_localtime FROM emissions
WHERE emissionid = :emissionid;