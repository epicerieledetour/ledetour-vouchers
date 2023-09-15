import pathlib
import random
import sqlite3
import string
from collections.abc import Generator
from sqlite3 import Connection
from typing import Any

import pydantic

from .. import models
from ..models import Emission, EmissionBase, EmissionId

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()
_SQL_EMISSION_CREATE = (_DIRPATH / "emission_create.sql").read_text()
_SQL_EMISSIONS_LIST = (_DIRPATH / "emissions_list.sql").read_text()
_SQL_EMISSION_READ = (_DIRPATH / "emission_read.sql").read_text()
_SQL_USER_CREATE = (_DIRPATH / "user_create.sql").read_text()
_SQL_USER_READ = (_DIRPATH / "user_read.sql").read_text()
_SQL_USERS_LIST = (_DIRPATH / "users_list.sql").read_text()
_SQL_USER_UPDATE = (_DIRPATH / "user_update.sql").read_text()
_SQL_USER_DELETE = (_DIRPATH / "user_delete.sql").read_text()

_USERID_ALPHABET = "23456789abcdefghijkmnopqrstuvwxyz"
_VOUCHERID_ALPHABET = string.ascii_uppercase

# Exceptions


class BaseException(Exception):
    pass


class UnknownId(BaseException):
    def __init__(self, Model: type[pydantic.BaseModel], id: Any):
        super().__init__()

        self._id = id
        self._Model = Model

    def __repr__(self):
        return f"{self.__class__.__name__}({self._Model!r}, {self._id!r})"

    def __str__(self):
        return f"Unknown {self._Model.__name__.lower()} {self._id}"


# Connection


def connect(path: pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.create_function("USERID", 2, _user_id)
    conn.create_function("VOUCHERID", 3, _voucher_id)
    return conn


def _sample(population: str, counts: int) -> str:
    return "".join(random.sample(population, counts))


def _user_id(userid: models.UserId, userlabel: str) -> str:
    return "tokusr_{}".format(_sample(_USERID_ALPHABET, 8))


def _voucher_id(
    voucherid: models.VoucherId, emissionid: models.EmissionId, sortnumber: int
) -> str:
    return "{:04d}-{}".format(sortnumber, _sample(_VOUCHERID_ALPHABET, 5))


# Init


def initdb(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL_INIT)


# Users


def create_user(conn: sqlite3.Connection, user: models.UserBase) -> models.User:
    cur = conn.execute(_SQL_USER_CREATE, user.model_dump())

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
    if not row:
        raise UnknownId(models.User, userid)
    return models.User(**row)


def list_users(conn: sqlite3.Connection) -> Generator[models.User, None, None]:
    cur = conn.execute(_SQL_USERS_LIST)
    for row in cur.fetchall():
        yield models.User(**row)


def update_user(conn: sqlite3.Connection, user: models.User) -> models.User:
    cur = conn.execute(_SQL_USER_UPDATE, user.model_dump())
    if cur.rowcount <= 0:
        raise UnknownId(models.User, user.userid)
    return read_user(conn, user.userid)


def delete_user(conn: sqlite3.Connection, userid: models.UserId) -> None:
    cur = conn.execute(_SQL_USER_DELETE, {"userid": userid})
    if cur.rowcount <= 0:
        raise UnknownId(models.User, userid)


# Emissions


def create_emission(conn: Connection, emission: EmissionBase) -> Emission:
    cur = conn.execute(_SQL_EMISSION_CREATE, emission.model_dump())

    # TODO: remove pragma no cover
    # See create_user
    if cur.lastrowid is None:
        raise RuntimeError("Could not create a new emission")  # pragma: no cover

    return read_emission(conn, models.EmissionId(cur.lastrowid))


def read_emission(conn: Connection, emissionid: EmissionId) -> Emission:
    row = conn.execute(_SQL_EMISSION_READ, {"emissionid": emissionid}).fetchone()
    if not row:
        raise UnknownId(Emission, emissionid)
    return Emission(**row)


def list_emissions(conn: Connection) -> Generator[Emission, None, None]:
    cur = conn.execute(_SQL_EMISSIONS_LIST)
    for row in cur.fetchall():
        yield Emission(**row)


def update_emission(conn: Connection, emission: Emission) -> Emission:
    cur = conn.execute(_SQL_EMISSION_UPDATE, emission.model_dump())
    if cur.rowcount <= 0:
        raise UnknownId(Emission, emission.emissionid)
    return read_emission(conn, emission.emissionid)


def delete_emission(conn: Connection, emissionid: EmissionId) -> None:
    cur = conn.execute(_SQL_EMISSION_DELETE, {"emissionid": emissionid})
    if cur.rowcount <= 0:
        raise UnknownId(Emission, emissionid)
