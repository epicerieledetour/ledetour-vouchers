import pathlib
import sqlite3

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()


def connect(path: pathlib.Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.create_function("USERID", 1, _user_id)
    conn.create_function("VOUCHERID", 1, _voucher_id)
    return conn


def initdb(conn: sqlite3.Connection):
    conn.executescript(_SQL_INIT)


def _user_id(userlabel):
    return "tokusr_{}".format(userlabel)


def _voucher_id(voucherid):
    return "tokvch_{}".format(voucherid)
