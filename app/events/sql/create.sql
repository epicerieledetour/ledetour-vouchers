INSERT OR REPLACE INTO events (id, bundleid, timestamp_utc, commandid, elemid, statusid)
VALUES (
    :id,
    :bundleid,
    DATETIME('now'),
    :commandid,
    :elemid,
    'status_ok'
);