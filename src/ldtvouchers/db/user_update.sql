UPDATE users
SET
    label=:label,
    can_cashin=:can_cashin,
    can_cashin_by_voucherid=:can_cashin_by_voucherid
WHERE userid=:userid;