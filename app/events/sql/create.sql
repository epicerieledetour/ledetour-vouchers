INSERT OR REPLACE INTO events (id, bundleid, timestamp_utc, userid, commandid, elemid, field, value, statusid)
VALUES (
    :id,
    :bundleid,
    DATETIME('now'),
    :userid,
    :commandid,
    :elemid,
    :field,
    :value,
    'status_ok'
);