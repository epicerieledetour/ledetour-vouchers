INSERT OR REPLACE INTO events (id, bundleid, timestamp_utc, commandid, elemid, field, value, statusid)
VALUES (
    :id,
    :bundleid,
    DATETIME('now'),
    :commandid,
    :elemid,
    :field,
    :value,
    'status_ok'
);