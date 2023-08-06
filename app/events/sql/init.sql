CREATE TABLE IF NOT EXISTS
enums (
    id TEXT NOT NULL PRIMARY KEY,
    enum TEXT NOT NULL,
    label TEXT NOT NULL
);

INSERT OR REPLACE INTO enums
VALUES
    ("status_ok", "status", "OK"),
    ("status_invalid_element", "status", "Invalid element"),
    ("status_invalid_command", "status", "Invalid command"),

    ("event_create", "event", "Create"),
    ("event_update", "event", "Update"),
    ("event_delete", "event", "Delete"),
    ("event_read", "event", "Read");

CREATE TABLE IF NOT EXISTS
events (
    id TEXT NOT NULL PRIMARY KEY,
    bundleid TEXT,
    timestamp_utc TEXT NOT NULL,
    commandid TEXT NOT NULL,
    elemid TEXT NOT NULL,
    field TEXT,
    value TEXT,
    statusid TEXT NOT NULL
);

-- TODO: extract this table to a elems module
CREATE VIEW IF NOT EXISTS
elems -- TODO: rename this entities
AS
SELECT elemid, field, value
FROM events
WHERE commandid == 'event_update'
GROUP BY elemid, field
HAVING MAX(rowid)
ORDER BY elemid, field;