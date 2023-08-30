import pathlib
import random
import sqlite3
import string
from typing import NewType

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()

_USERID_ALPHABET = "23456789abcdefghijkmnopqrstuvwxyz"
_VOUCHERID_ALPHABET = string.ascii_uppercase

EmissionId = NewType("EmissionId", int)
UserId = NewType("UserId", int)
VoucherId = NewType("VoucherId", int)


def connect(path: pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.create_function("USERID", 2, _user_id)
    conn.create_function("VOUCHERID", 3, _voucher_id)
    return conn


def initdb(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL_INIT)


def _sample(population: str, counts: int) -> str:
    return "".join(random.sample(population, counts))


def _user_id(userid: UserId, userlabel: str) -> str:
    return "tokusr_{}".format(_sample(_USERID_ALPHABET, 8))


def _voucher_id(voucherid: VoucherId, emissionid: EmissionId, sortnumber: int) -> str:
    return "{:04d}-{}".format(sortnumber, _sample(_VOUCHERID_ALPHABET, 5))
