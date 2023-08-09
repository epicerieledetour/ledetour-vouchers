DELETE FROM emission_contents
WHERE emissionid = :emissionid
AND sortnumber IN ({sortnumbers_string})