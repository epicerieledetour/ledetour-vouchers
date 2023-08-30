import pathlib
import random
import sqlite3
import string

from .. import models

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()
_SQL_USER_CREATE = (_DIRPATH / "user_create.sql").read_text()
_SQL_USER_READ = (_DIRPATH / "user_read.sql").read_text()

_USERID_ALPHABET = "23456789abcdefghijkmnopqrstuvwxyz"
_VOUCHERID_ALPHABET = string.ascii_uppercase


def connect(path: pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.create_function("USERID", 2, _user_id)
    conn.create_function("VOUCHERID", 3, _voucher_id)
    return conn


def initdb(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(_SQL_INIT)


def _sample(population: str, counts: int) -> str:
    return "".join(random.sample(population, counts))


def _user_id(userid: models.UserId, userlabel: str) -> str:
    return "tokusr_{}".format(_sample(_USERID_ALPHABET, 8))


def _voucher_id(
    voucherid: models.VoucherId, emissionid: models.EmissionId, sortnumber: int
) -> str:
    return "{:04d}-{}".format(sortnumber, _sample(_VOUCHERID_ALPHABET, 5))


# Users


def create_user(conn: sqlite3.Connection, user: models.UserBase) -> models.User:
    with conn:
        cur = conn.cursor()
        cur.execute(_SQL_USER_CREATE, user.model_dump())

        # TODO: remove no cover pragma
        # Cursor.lastrowid type is int | None, but read_user requires UserId (int)
        # only. For mypy we hence need to handle the case where lastrowid is None.
        # However I couldn't find a simple way to mock lastrowid to be None:
        # - In the test code, cur.execute([a statement that returns no row]) always set
        #   lastrowid to 2 for some reason even if lastrowid is initially None
        # - Connection and Cursor are frozen classes so unittest.mock can't patch them
        #
        # I resorted to pragma: no cover the exception raise. Hopefully there will be
        # a moment to take another look at that later.

        if cur.lastrowid is None:
            raise RuntimeError("Could not create a new user")  # pragma: no cover

        return read_user(conn, models.UserId(cur.lastrowid))


def read_user(conn: sqlite3.Connection, userid: models.UserId) -> models.User:
    row = conn.execute(_SQL_USER_READ, (userid,)).fetchone()
    return models.User(**row)
