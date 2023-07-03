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
    ("event_delete", "event", "Delete"),
    ("event_read", "event", "Read"),
    ("event_update", "event", "Update");

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
