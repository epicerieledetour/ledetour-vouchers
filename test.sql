.mode column

CREATE TABLE emissions (
    emissionid INTEGER PRIMARY KEY,
    expiration_utc TEXT NOT NULL
);

CREATE TABLE users (
    userid INTEGER PRIMARY KEY,
    label TEXT NOT NULL
);

CREATE TABLE vouchers (
    voucherid INTEGER PRIMARY KEY,
    emissionid INTEGER NOT NULL,
    sortnumber INTEGER NOT NULL,
    cashedin_by INTEGER,
    cashedin_utc TEXT,

    FOREIGN KEY(emissionid) REFERENCES emissions(emissionid),
    FOREIGN KEY(cashedin_by) REFERENCES users(userid)
);

CREATE TABLE levels (
    levelid TEXT PRIMARY KEY
);
INSERT INTO levels (levelid)
VALUES
    ("ok"),
    ("warning"),
    ("error");


CREATE TABLE responses (
    responseid TEXT PRIMARY KEY,
    httpcode INTEGER NOT NULL,
    levelid TEXT NOT NULL,
    set_cashin INTEGER,
    can_undo INTEGER,
    description TEXT,

    FOREIGN KEY(levelid) REFERENCES levels(levelid)
);
INSERT INTO responses (responseid, httpcode, levelid, set_cashin, can_undo, description)
VALUES
    (
        "error_voucher_unauthentified", 401, "error", NULL, NULL,
        "Invalid user authorization"
    ),
    (
        "error_voucher_invalid_token", 404, "error", NULL, NULL,
        "Invalid voucher"
    ),
    (
        "error_voucher_expired", 403, "error", NULL, NULL,
        "Voucher has expired"
    ),
    (
        "ok_voucher_cashedin", 200, "ok", 1, 1,
        "Voucher cashedin"
    ),
    (
        "error_voucher_cashedin_by_another_user", 403, "error", NULL, NULL,
        "Voucher has already cashedin by another user"
    ),
    (
        "warning_voucher_cannot_undo_cashedin", 200, "warning", NULL, NULL,
        "Voucher has already been cashed by the user but too long ago so it can't be undone"
    ),
    (
        "warning_voucher_can_undo_cashedin", 200, "warning", NULL, 1,
        "Voucher has already been cashed in by the user but recently enough so they can still undo"
    ),
    (
        "error_user_invalid_token", 401, "error", NULL, NULL,
        "User auth token can not be found"
    ),
    (
        "ok_user_authentified", 200, "error", NULL, NULL,
        "User has been authentified"
    )
;

CREATE TABLE actions (
    actionid INTEGER PRIMARY KEY,
    timestamp_utc DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    req_usertoken TEXT,
    req_vouchertoken TEXT,
    userid INTEGER,
    voucherid INTEGER,
    request TEXT NOT NULL,
    responseid TEXT,

    FOREIGN KEY(req_usertoken) REFERENCES tokens(token),
    FOREIGN KEY(req_vouchertoken) REFERENCES tokens(token),
    FOREIGN KEY(userid) REFERENCES users(userid),
    FOREIGN KEY(voucherid) REFERENCES vouchers(voucherid),
    FOREIGN KEY(responseid) REFERENCES responses(responseid)
);

CREATE TABLE tokens (
    token TEXT PRIMARY KEY NOT NULL,
    tablename TEXT NOT NULL,
    idintable INTEGER NOT NULL
);

CREATE TRIGGER create_token_on_new_user
AFTER INSERT ON users
BEGIN
    INSERT INTO tokens
    VALUES
        (
            -- printf("user_%s", lower(hex(randomblob(8)))),
            printf("tokusr_%s", new.label),
            "users",
            new.userid
        );
END;

CREATE TRIGGER create_token_on_new_voucher
AFTER INSERT ON vouchers
BEGIN
    INSERT INTO tokens
    VALUES
        (
            -- printf("vchr_%s", lower(hex(randomblob(8)))),
            printf("tokvch_%s", new.voucherid),
            "vouchers",
            new.voucherid
        );
END;

--CREATE TRIGGER update_voucher_on_action
--INSERT ON actions
--BEGIN
--    UPDATE vouchers
--    SET
--    cashedin_by = new.userid,
--    cashedin_utc = new.timestamp_utc
--    FROM vouchers v
--    JOIN actions a ON a.actionid = new.actionid
--    JOIN responses r ON r.responseid = a.responseid
--    WHERE voucherid = new.voucherid;
--END;

CREATE VIEW dectree AS
SELECT
    actionid,
    req_usertoken,
    req_vouchertoken,
    request,
    '',
    userid,
    voucherid,
    expiration_utc,
    timestamp_utc,
    expiration_utc > timestamp_utc,
    '',
    CASE
        WHEN req_vouchertoken IS NOT NULL
        THEN  -- Voucher scan
            CASE
                WHEN userid IS NULL THEN "error_voucher_unauthentified"  -- 401
                WHEN voucherid IS NULL THEN "error_voucher_invalid_token"  -- 404
                WHEN timestamp_utc > expiration_utc THEN "error_voucher_expired"  -- 403
                WHEN cashedin_by IS NULL THEN "ok_voucher_cashedin"  -- 200
                WHEN cashedin_by != userid THEN "error_voucher_cashedin_by_another_user" -- 403
                WHEN cashedin_utc < date('now','-15 min') THEN "warning_voucher_cannot_undo_cashedin" -- 200
                ELSE "warning_voucher_can_undo_cashedin"  -- 200
            END
        ELSE  -- Auth scan
            CASE
                WHEN userid IS NULL THEN "error_user_invalid_token"  -- Tested
                ELSE "ok_user_authentified"  -- Tested
            END
    END
    AS response
FROM actions a
LEFT JOIN tokens tku ON a.req_usertoken = tku.token
LEFT JOIN users u ON tku.tablename = 'users' AND tku.idintable = u.userid
LEFT JOIN tokens tkv ON a.req_vouchertoken = tkv.token
LEFT JOIN vouchers v ON tkv.tablename = 'vouchers' AND tkv.idintable = v.voucherid
LEFT JOIN emissions e ON v.emissionid = e.emissionid;
-- LEFT JOIN vouchers ON tokens.tablename = 'vouchers' AND tokens.idintable = vouchers.voucherid;

CREATE TRIGGER compute_action_response
AFTER INSERT ON actions
BEGIN
    UPDATE actions
    SET
        userid = COALESCE(a.userid, u.userid),
	voucherid = COALESCE(a.voucherid, v.voucherid),
        responseid =
    CASE
        WHEN actions.req_vouchertoken IS NOT NULL
        THEN  -- Voucher scan
            CASE
                WHEN u.userid IS NULL THEN "error_voucher_unauthentified"  -- 401
                WHEN v.voucherid IS NULL THEN "error_voucher_invalid_token"  -- 404
                WHEN actions.timestamp_utc > expiration_utc THEN "error_voucher_expired"  -- 403
                WHEN cashedin_by IS NULL THEN "ok_voucher_cashedin"  -- 200
                WHEN cashedin_by != u.userid THEN "error_voucher_cashedin_by_another_user" -- 403
                WHEN cashedin_utc < date('now','-15 min') THEN "warning_voucher_cannot_undo_cashedin" -- 200
                ELSE "warning_voucher_can_undo_cashedin"  -- 200
            END
        ELSE  -- Auth scan
            CASE
                WHEN u.userid IS NULL THEN "error_user_invalid_token"  -- Tested
                ELSE "ok_user_authentified"  -- Tested
            END
    END
    FROM actions a
        LEFT JOIN tokens tku ON a.req_usertoken = tku.token
        LEFT JOIN users u ON tku.tablename = 'users' AND tku.idintable = u.userid
        LEFT JOIN tokens tkv ON a.req_vouchertoken = tkv.token
        LEFT JOIN vouchers v ON tkv.tablename = 'vouchers' AND tkv.idintable = v.voucherid
        LEFT JOIN emissions e ON v.emissionid = e.emissionid	
    WHERE actions.actionid = new.actionid;
END;

INSERT INTO emissions (expiration_utc)
VALUES
    (date('now', '+3 month')),
    (date('now', '-3 month'));

INSERT INTO users (label)
VALUES
    ("ADMIN"),
    ("cashier"),
    ("cashier2");

INSERT INTO vouchers (emissionid, sortnumber)
VALUES
    (1, 1),
    (2, 1);


-- Voucher

-- error_voucher_unauthentified
INSERT INTO actions (req_vouchertoken, request)
VALUES ("tokvch_2", "scan");

-- error_voucher_invalid_token
INSERT INTO actions (req_usertoken, req_vouchertoken, request)
VALUES ("tokusr_cashier", "tokvch_invalid", "scan");

-- error_voucher_expired
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, request)
VALUES ("tokusr_cashier", "tokvch_1", date('now', '+4 month'), "scan");

-- ok_voucher_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, request)
VALUES ("tokusr_cashier", "tokvch_1", "scan");

-- error_voucher_cashedin_by_another_user
INSERT INTO actions (req_usertoken, req_vouchertoken, request)
VALUES ("tokusr_cashier2", "tokvch_1", "scan");

-- ok_voucher_cannot_undo_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, request)
VALUES ("tokusr_cashier", "tokvch_1", date('now', '+ 30min'), "scan");

-- ok_voucher_can_undo_cashedin
INSERT INTO actions (req_usertoken, req_vouchertoken, timestamp_utc, request)
VALUES ("tokusr_cashier", "tokvch_1", date('now', '+ 1min'), "scan");


-- User

-- error_user_invalid_token
INSERT INTO actions (req_usertoken, request)
VALUES ("tokusr_invalid", "scan");

-- ok_user_authentified
INSERT INTO actions (req_usertoken, request)
VALUES ("tokusr_cashier", "scan");


-- Selects

SELECT * FROM responses;
SELECT * FROM users;
SELECT * FROM emissions;
SELECT * FROM vouchers;
SELECT * FROM tokens;
SELECT * FROM actions;
SELECT * FROM dectree;



-- TODO
-- + Trigger to create a response row
-- - Trigger to set voucher status
-- - Continue tests
-- - Add undo
-- - Add set
-- - Write decision tree in doc
