UPDATE emissions
SET
    label=:label,
    expiration_utc=:expiration_utc
WHERE emissionid=:emissionid;