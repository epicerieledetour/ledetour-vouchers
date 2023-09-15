INSERT INTO vouchers(
    emissionid,
    sortnumber,
    value_CAN,
    distributed_by
)
SELECT
    :emissionid,
    :sortnumber,
    :value_CAN,
    COALESCE(users.userid, NULL)
FROM users
WHERE users.label = :distributed_by_label;