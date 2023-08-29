import pathlib
import sqlite3

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()


def connect(path: pathlib.Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initdb(conn: sqlite3.Connection):
    conn.executescript(_SQL_INIT)
