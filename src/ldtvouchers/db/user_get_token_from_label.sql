SELECT token
FROM users, tokens
ON users.userid = tokens.idintable AND tokens.tablename = "users"
WHERE users.label = :userlabel