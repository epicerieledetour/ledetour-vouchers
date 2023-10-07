import functools
import pathlib
import random
import sqlite3
import string
from collections.abc import Generator
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Any

import pydantic

from .. import models
from ..models import Emission, EmissionBase, EmissionId, PublicEmission

_DIRPATH = pathlib.Path(__file__).parent

_SQL_INIT = (_DIRPATH / "init.sql").read_text()
_SQL_ACTION_CREATE = (_DIRPATH / "action_create.sql").read_text()
_SQL_EMISSION_CREATE = (_DIRPATH / "emission_create.sql").read_text()
_SQL_EMISSIONS_LIST = (_DIRPATH / "emissions_list.sql").read_text()
_SQL_EMISSION_READ = (_DIRPATH / "emission_read.sql").read_text()
_SQL_EMISSION_UPDATE = (_DIRPATH / "emission_update.sql").read_text()
_SQL_EMISSION_DELETE = (_DIRPATH / "emission_delete.sql").read_text()
_SQL_USER_CREATE = (_DIRPATH / "user_create.sql").read_text()
_SQL_USER_READ = (_DIRPATH / "user_read.sql").read_text()
_SQL_USER_READ_PUBLIC = (_DIRPATH / "user_read_public.sql").read_text()
_SQL_USERS_LIST = (_DIRPATH / "users_list.sql").read_text()
_SQL_USER_UPDATE = (_DIRPATH / "user_update.sql").read_text()
_SQL_USER_DELETE = (_DIRPATH / "user_delete.sql").read_text()
_SQL_VOUCHER_CREATE = (_DIRPATH / "voucher_create.sql").read_text()
_SQL_VOUCHERS_LIST = (_DIRPATH / "vouchers_list.sql").read_text()
_SQL_VOUCHERS_LIST_PUBLIC = (_DIRPATH / "vouchers_list_public.sql").read_text()
_SQL_VOUCHERS_DELETE = (_DIRPATH / "vouchers_delete.sql").read_text()

_USERID_ALPHABET = "23456789abcdefghijkmnopqrstuvwxyz"
_VOUCHERID_ALPHABET = string.ascii_uppercase


@functools.cache
def get_sql(name: str) -> str:
    return (_DIRPATH / f"{name}.sql").read_text()


# Exceptions


class BaseException(Exception):
    pass


class UnknownId(BaseException):
    def __init__(self, Model: type[pydantic.BaseModel], id: Any):
        super().__init__()

        self._id = id
        self._Model = Model

    def __str__(self):
        return f"Unknown {self._Model.__name__.lower()} {self._id}"


class VoucherCreationError(BaseException):
    def __init__(self, emissionid: EmissionId, voucher: models.VoucherImport):
        super().__init__(voucher)

        self.emissionid = emissionid
        self.voucher = voucher


class ActionError(BaseException):
    def __init__(self, action: models.Action):
        super().__init__()

        self.action = action


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


def read_public_user(conn: sqlite3.Connection, userid: models.UserId) -> models.User:
    row = conn.execute(_SQL_USER_READ_PUBLIC, {"userid": userid}).fetchone()
    if not row:
        raise UnknownId(models.User, userid)
    return models.PublicUser(**row)


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


def _read_vouchers(
    conn: Connection, emissionid: EmissionId
) -> Generator[models.Voucher, None, None]:
    cur = conn.execute(_SQL_VOUCHERS_LIST, {"emissionid": emissionid})
    for row in cur.fetchall():
        yield models.Voucher(**row)


def _read_public_vouchers(
    conn: Connection, emissionid: EmissionId
) -> Generator[models.PublicVoucher, None, None]:
    cur = conn.execute(_SQL_VOUCHERS_LIST_PUBLIC, {"emissionid": emissionid})
    for row in cur.fetchall():
        yield models.PublicVoucher(**row)


def read_emission(conn: Connection, emissionid: EmissionId) -> Emission:
    row = conn.execute(_SQL_EMISSION_READ, {"emissionid": emissionid}).fetchone()
    if not row:
        raise UnknownId(Emission, emissionid)
    return Emission(
        vouchers=list(_read_vouchers(conn, emissionid)),
        **row,
    )


def read_public_emission(conn: Connection, emissionid: EmissionId) -> PublicEmission:
    row = conn.execute(_SQL_EMISSION_READ, {"emissionid": emissionid}).fetchone()
    if not row:
        raise UnknownId(Emission, emissionid)
    return PublicEmission(
        vouchers=list(_read_public_vouchers(conn, emissionid)),
        **row,
    )


def list_emissions(conn: Connection) -> Generator[Emission, None, None]:
    cur = conn.execute(_SQL_EMISSIONS_LIST)
    for row in cur.fetchall():
        yield Emission(
            vouchers=list(_read_vouchers(conn, row["emissionid"])),
            **row,
        )


def update_emission(conn: Connection, emission: Emission) -> Emission:
    cur = conn.execute(_SQL_EMISSION_UPDATE, emission.model_dump())
    if cur.rowcount <= 0:
        raise UnknownId(Emission, emission.emissionid)
    return read_emission(conn, emission.emissionid)


def delete_emission(conn: Connection, emissionid: EmissionId) -> None:
    cur = conn.execute(_SQL_EMISSION_DELETE, {"emissionid": emissionid})
    if cur.rowcount <= 0:
        raise UnknownId(Emission, emissionid)


@contextmanager
def set_emission_vouchers(conn: Connection, emissionid: EmissionId) -> None:
    sortnumber = 0

    def add_voucher(voucher: models.VoucherImport) -> None:
        nonlocal sortnumber

        sortnumber += 1

        args = {
            "emissionid": emissionid,
            "sortnumber": sortnumber,
            **voucher.model_dump(),
        }
        cur = conn.execute(_SQL_VOUCHER_CREATE, args)
        if cur.rowcount == 0:
            raise VoucherCreationError(emissionid, voucher)

    conn.execute(_SQL_VOUCHERS_DELETE, {"emissionid": emissionid})

    yield add_voucher


def add_action(conn: Connection, action: models.ActionBase) -> models.Action:
    cur = conn.execute(_SQL_ACTION_CREATE, action.model_dump())
    if cur.rowcount == 0:
        raise ActionError(action)

    # TODO: test return value
    return _read_action(conn, models.EmissionId(cur.lastrowid))


def _read_action(conn: Connection, actionid: models.ActionId) -> models.Action:
    row = conn.execute(get_sql("action_read"), {"actionid": actionid}).fetchone()
    if not row:
        raise UnknownId(Emission, actionid)
    return models.Action(**row)


def build_http_response(
    conn: Connection, action: models.Action
) -> tuple[models.HttpStatusCode, models.HttpResponse]:
    # Code and Status

    row = conn.execute(
        get_sql("http_response_read", {"responseid": action.responseid})
    ).fetchone()
    resp = dict(**row)
    code = resp.pop("httpcode")

    status = models.HttpResponseStatus(
        level=resp["levelid"],
        description=resp["description"],
    )

    # User

    user = None
    if action.userid:
        row = conn.execute(
            get_sql("http_user_read", {"responseid": action.responseid})
        ).fetchone()
        user = read_public_user(conn, action.userid)

    # Voucher

    voucher = None
    if action.voucherid:
        args = {"voucherid": action.voucherid}
        rows = conn.execute("http_voucher_actions_read", args).fetchall()
        history = [models.HttpAction(**row) for row in rows]

        row = conn.execute("http_voucher_read", args).fetchall()
        voucher = models.HttpVoucher(history=history, **row)

    # Return

    return code, models.HttpResponse(status=status, user=user, voucher=voucher)


def _read_response():
    pass


# Debug

import datetime
import random


def filldb(conn: Connection) -> None:
    values = [5, 10, 20, 50]
    bools = (False, True)

    users_dist = []
    for i in range(random.randint(3, 6)):
        label = f"dist{i:04d}"
        users_dist.append(
            create_user(
                conn,
                models.UserBase(
                    label=f"dist{i:02d}",
                    description=f"User {label}",
                    can_cashin=False,
                    can_cashin_by_voucherid=False,
                ),
            )
        )

    users_cash = []
    for i in range(random.randint(3, 6)):
        can_cashin_by_voucherid = random.choice(bools)
        label = f"cash{i:02d}{'-v' if can_cashin_by_voucherid else ''}"

        users_cash.append(
            create_user(
                conn,
                models.UserBase(
                    label=label,
                    description=f"User {label}",
                    can_cashin=True,
                    can_cashin_by_voucherid=can_cashin_by_voucherid,
                ),
            )
        )

    vouchers = []
    for i in range(random.randint(3, 5)):
        now = datetime.datetime.now().date().replace(day=1)

        emission = create_emission(
            conn,
            models.EmissionBase(
                label=f"Em{i:02d}",
                expiration_utc=now + datetime.timedelta(days=90 + 30 * i),
            ),
        )

        with set_emission_vouchers(conn, emission.emissionid) as add_voucher:
            for _ in range(random.randrange(80, 100, 10)):
                add_voucher(
                    models.VoucherImport(
                        value_CAN=random.choice(values),
                        distributed_by_label=random.choice(users_dist).label,
                    )
                )

        vouchers.extend(_read_public_vouchers(conn, emission.emissionid))

    users_cash = [read_public_user(conn, user.userid) for user in users_cash]
    for i in range(random.randint(len(vouchers) * 3, len(vouchers) * 5)):
        has_user = random.random() < 0.99
        has_voucher = random.random() < 0.95
        add_action(
            conn,
            models.ActionBase(
                origin="debug",
                req_usertoken=random.choice(users_cash).token if has_user else None,
                req_vouchertoken=random.choice(vouchers).token if has_voucher else None,
                requestid="scan" if random.random() < 0.95 else "undo",
            ),
        )
