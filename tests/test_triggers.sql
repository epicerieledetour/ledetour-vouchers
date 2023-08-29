
-- Inserts

INSERT INTO emissions (expiration_utc)
VALUES
    (date('now', '+3 month')),
    (date('now', '-3 month'));

INSERT INTO users (label, can_cashin, can_cashin_by_voucherid)
VALUES
    ("dist", FALSE, FALSE),
    ("cashier", TRUE, FALSE),
    ("cashier2", TRUE, TRUE);

INSERT INTO vouchers (emissionid, sortnumber)
VALUES
    (1, 1),  -- 1
    (1, 2),  -- 2
    (2, 1),  -- 3
    (1, 3),  -- 4
    (1, 4);  -- 5


-- Voucher

-- 1: error_voucher_unauthentified
INSERT INTO actions (req_vouchertoken, requestid)
VALUES ("tokvch_2", "scan");

-- 2: error_voucher_user_needs_voucher_token
INSERT INTO actions (req_usertoken, voucherid, requestid)
VALUES ("tokusr_cashier", 4, "scan");

-- 3: ok_voucher_cashedin
-- User can cash in using a voucherid directly, without a voucher token
INSERT INTO actions (req_usertoken, voucherid, requestid)
VALUES ("tokusr_cashier2", 5, "scan"); 

-- 4: error_voucher_invalid
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier", "tokvch_invalid", "scan");

-- 5: error_voucher_expired
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, requestid)
VALUES ("tokusr_cashier", "tokvch_1", datetime('now', '+4 month'), "scan");

-- 6: ok_voucher_info on a voucher that has not been cashedin by an user with no can_cashin right
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_dist", "tokvch_2", "scan");

-- 7: ok_voucher_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier", "tokvch_1", "scan");

-- 8: error_voucher_cannot_undo_not_cashedin
-- A voucher cannot been undone if not cashedin first
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier", "tokvch_2", "undo");

-- 9: ok_voucher_info on a voucher that has been cashedin by an user with no can_cashin right
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_dist", "tokvch_1", "scan");

-- 10: error_voucher_cashedin_by_another_user
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier2", "tokvch_1", "scan");

-- 11: warning_voucher_cannot_undo_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, requestid)
VALUES ("tokusr_cashier", "tokvch_1", datetime('now', '+6 minute'), "scan");

-- 12: error_voucher_cannot_undo_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, requestid)
VALUES ("tokusr_cashier", "tokvch_1", datetime('now', '+6 minute'), "undo");

-- 13: error_system_unexpected_request
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, requestid)
VALUES ("tokusr_cashier", "tokvch_1", datetime('now', '+6 minute'), "other_action");

-- 14: warning_voucher_can_undo_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, requestid)
VALUES ("tokusr_cashier", "tokvch_1", datetime('now', '+1 minute'), "scan");

-- 15-16: ok_voucher_cashedin / ok_voucher_undo
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier", "tokvch_2", "scan");
INSERT INTO actions (req_usertoken, req_vouchertoken, requestid)
VALUES ("tokusr_cashier", "tokvch_2", "undo");


-- User

-- 17: error_user_invalid_token
INSERT INTO actions (req_usertoken, requestid)
VALUES ("tokusr_invalid", "scan");

-- 18: ok_user_authentified
INSERT INTO actions (req_usertoken, requestid)
VALUES ("tokusr_cashier", "scan");
