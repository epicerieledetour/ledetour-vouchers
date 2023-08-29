CREATE TABLE IF NOT EXISTS
emissions (
    emissionid INTEGER PRIMARY KEY,
    expiration_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS
users (
    userid INTEGER PRIMARY KEY,
    label TEXT NOT NULL,
    can_cashin BOOLEAN DEFAULT FALSE,
    can_cashin_by_voucherid BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS
vouchers (
    voucherid INTEGER PRIMARY KEY,
    emissionid INTEGER NOT NULL,
    sortnumber INTEGER NOT NULL,
    cashedin_by INTEGER,
    cashedin_utc DATETIME,
    undo_expiration_utc DATETIME,

    FOREIGN KEY(emissionid) REFERENCES emissions(emissionid),
    FOREIGN KEY(cashedin_by) REFERENCES users(userid)
);

CREATE TABLE IF NOT EXISTS
levels (
    levelid TEXT PRIMARY KEY
);
INSERT INTO levels (levelid)
VALUES
    ("ok"),
    ("warning"),
    ("error");


CREATE TABLE IF NOT EXISTS
responses (
    responseid TEXT PRIMARY KEY,
    httpcode INTEGER NOT NULL,
    levelid TEXT NOT NULL,
    set_cashin INTEGER,
    undo_timeout_datefunc_modifier TEXT,  -- Modifier like "+5 minute" used in date functions, see https://www.sqlite.org/lang_datefunc.html
    can_undo INTEGER,
    description TEXT,

    FOREIGN KEY(levelid) REFERENCES levels(levelid)
);
INSERT INTO responses (responseid, httpcode, levelid, set_cashin, undo_timeout_datefunc_modifier, can_undo, description)
VALUES
    (
        "error_voucher_unauthentified", 401, "error", NULL, NULL, NULL,
        "Invalid user authorization"
    ),
    (
        "error_voucher_user_needs_voucher_token", 401, "error", NULL, NULL, NULL,
        "User requires a voucher token"
    ),
    (
        "error_voucher_invalid", 404, "error", NULL, NULL, NULL,
        "Invalid voucher"
    ),
    (
        "error_voucher_expired", 403, "error", NULL, NULL, NULL,
        "Voucher has expired"
    ),
    (
        "ok_voucher_cashedin", 200, "ok", 1, "+5 minute", 1,
        "Voucher cashedin"
    ),
    (
        "error_voucher_cashedin_by_another_user", 403, "error", NULL, NULL, NULL,
        "Voucher has already cashedin by another user"
    ),
    (
        "warning_voucher_cannot_undo_cashedin", 200, "warning", NULL, NULL, NULL,
        "Voucher has already been cashed by the user but too long ago so it can't be undone"
    ),
    (
        "warning_voucher_can_undo_cashedin", 200, "warning", NULL, 1, NULL,
        "Voucher has already been cashed in by the user but recently enough so they can still undo"
    ),
    (
        "error_user_invalid_token", 401, "error", NULL, NULL, NULL,
        "User auth token can not be found"
    ),
    (
        "ok_user_authentified", 200, "ok", NULL, NULL, NULL,
        "User has been authentified"
    ),
    (
        "ok_voucher_info", 200, "ok", NULL, NULL, NULL,
        "User read the voucher without changing its state"
    ),
    (
	"error_voucher_cannot_undo_cashedin", 403, "error", NULL, NULL, NULL,
	"It is not possible to undo a cashedin voucher anymore"
    ),
    (
	"error_system_unexpected_request", 500, "error", NULL, NULL, NULL,
	"Unexpected request led to an internal error"
    ),
    (
	"ok_voucher_undo", 200, "ok", 0, NULL, NULL,
	"A voucher previously cashedin has been undone"
    ),
    (
	"error_voucher_cannot_undo_not_cashedin", 403, "error", NULL, NULL, NULL,
	"A voucher can not been undone if not cashedin first"
    )
;

CREATE TABLE IF NOT EXISTS
requests (
    requestid TEXT NOT NULL PRIMARY KEY
);
INSERT INTO requests (requestid)
VALUES
    ("scan"),
    ("undo");

CREATE TABLE IF NOT EXISTS
actions (
    actionid INTEGER PRIMARY KEY,
    timestamp_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    req_usertoken TEXT,
    req_vouchertoken TEXT,
    userid INTEGER,
    voucherid INTEGER,
    requestid TEXT NOT NULL,
    responseid TEXT,

    FOREIGN KEY(req_usertoken) REFERENCES tokens(token),
    FOREIGN KEY(req_vouchertoken) REFERENCES tokens(token),
    FOREIGN KEY(userid) REFERENCES users(userid),
    FOREIGN KEY(voucherid) REFERENCES vouchers(voucherid),
    FOREIGN KEY(requestid) REFERENCES requests(requestid),
    FOREIGN KEY(responseid) REFERENCES responses(responseid)
);

CREATE TABLE IF NOT EXISTS
tokens (
    token TEXT PRIMARY KEY NOT NULL,
    tablename TEXT NOT NULL,
    idintable INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS
create_token_on_new_user
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

CREATE TRIGGER IF NOT EXISTS
create_token_on_new_voucher
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

CREATE TRIGGER IF NOT EXISTS
update_voucher_on_action
AFTER UPDATE OF responseid ON actions
BEGIN
    UPDATE vouchers
    SET
        cashedin_by =
            CASE
                WHEN r.set_cashin IS NULL THEN vouchers.cashedin_by
                WHEN r.set_cashin = 0 THEN NULL
                WHEN r.set_cashin = 1 THEN new.userid
            END,
        cashedin_utc =
            CASE
                WHEN r.set_cashin IS NULL THEN vouchers.cashedin_utc
                WHEN r.set_cashin = 0 THEN NULL
                WHEN r.set_cashin = 1 THEN new.timestamp_utc
            END,
        undo_expiration_utc =
            CASE
                WHEN r.set_cashin IS NULL THEN vouchers.undo_expiration_utc
                WHEN r.set_cashin = 0 THEN NULL
                WHEN r.set_cashin = 1 THEN datetime(a.timestamp_utc, r.undo_timeout_datefunc_modifier)
            END
    FROM vouchers v
    LEFT JOIN actions a ON a.actionid = new.actionid
    LEFT JOIN responses r ON r.responseid = a.responseid
    WHERE vouchers.voucherid = new.voucherid;
END;

CREATE TRIGGER IF NOT EXISTS
compute_action_response
AFTER INSERT ON actions
BEGIN
    UPDATE actions
    SET
        userid = COALESCE(a.userid, u.userid),
	    voucherid = COALESCE(a.voucherid, v.voucherid),
        responseid =
    CASE
        WHEN a.req_vouchertoken IS NULL AND a.voucherid IS NULL  -- Q1
            THEN  -- Auth scan
                CASE
                    WHEN u.userid IS NULL  -- Q2
                        THEN "error_user_invalid_token"
                        ELSE "ok_user_authentified"
                END

            ELSE  -- Voucher scan
                CASE
                    WHEN a.requestid NOT IN (SELECT requestid FROM requests)  -- Q13
                        THEN "error_system_unexpected_request"
                    WHEN u.userid IS NULL  -- Q3
                        THEN "error_voucher_unauthentified"
                    WHEN u.can_cashin_by_voucherid = FALSE AND a.req_vouchertoken IS NULL
                        THEN "error_voucher_user_needs_voucher_token"
                    WHEN v.voucherid IS NULL  -- Q4
                        THEN "error_voucher_invalid"
                    WHEN a.timestamp_utc > expiration_utc  -- Q5
                        THEN "error_voucher_expired"
                    WHEN NOT u.can_cashin  -- Q9
                        THEN "ok_voucher_info"
                    WHEN v.cashedin_by IS NULL  -- Q6
                        THEN
                            CASE  -- Q10
                                WHEN a.requestid = 'scan'
                                    THEN "ok_voucher_cashedin"
                                WHEN a.requestid = 'undo'
                                    THEN "error_voucher_cannot_undo_not_cashedin"
                            END
                    WHEN v.cashedin_by != u.userid  -- Q7
                        THEN "error_voucher_cashedin_by_another_user"
                    WHEN a.timestamp_utc > v.undo_expiration_utc  -- Q8
                        THEN
                            CASE
                                WHEN a.requestid = 'scan'  -- Q11
                                    THEN "warning_voucher_cannot_undo_cashedin"
                                WHEN a.requestid = 'undo'
                                    THEN "error_voucher_cannot_undo_cashedin"
                            END
		            ELSE
		                CASE
			                WHEN a.requestid = 'scan'  -- Q12
			                    THEN "warning_voucher_can_undo_cashedin"
			                WHEN a.requestid = 'undo'
				                THEN "ok_voucher_undo"
			            END
	            END
    END
    FROM actions a
        LEFT JOIN tokens tku ON a.req_usertoken = tku.token
        LEFT JOIN users u ON tku.tablename = 'users' AND tku.idintable = u.userid
        LEFT JOIN tokens tkv ON a.req_vouchertoken = tkv.token
        LEFT JOIN vouchers v ON COALESCE(a.voucherid, tkv.idintable) = v.voucherid
        LEFT JOIN emissions e ON v.emissionid = e.emissionid	
    WHERE actions.actionid = new.actionid;
END;
