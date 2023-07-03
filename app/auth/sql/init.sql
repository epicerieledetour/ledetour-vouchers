CREATE TABLE IF NOT EXISTS
aces (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT,
);

CREATE TABLE IF NOT EXISTS
acls (
    id
);

CREATE TABLE IF NOT EXISTS
tokens (
    id TEXT NOT NULL,
    token TEXT NOT NULL
);
