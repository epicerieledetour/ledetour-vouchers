import pathlib
import random
import sqlite3
import string

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()

_USERID_ALPHABET = "23456789abcdefghijkmnopqrstuvwxyz"
_VOUCHERID_ALPHABET = string.ascii_uppercase


def connect(path: pathlib.Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.create_function("USERID", 2, _user_id)
    conn.create_function("VOUCHERID", 3, _voucher_id)
    return conn


def initdb(conn: sqlite3.Connection):
    conn.executescript(_SQL_INIT)


def _sample(population, counts):
    return "".join(random.sample(population, counts))


def _user_id(userid, userlabel):
    return "tokusr_{}".format(_sample(_USERID_ALPHABET, 8))


def _voucher_id(voucherid, emissionid, sortnumber):
    return "{:04d}-{}".format(sortnumber, _sample(_VOUCHERID_ALPHABET, 5))
