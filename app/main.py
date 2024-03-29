import datetime
import os
import pathlib
import random
import string

from collections.abc import Callable
from dataclasses import dataclass

from typing import Dict, List, Union


import sqlite3
from sqlite3 import connect, Connection, Row

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from . import utils

DB_PATH = pathlib.Path(
    os.environ.get("LDTVOUCHERS_DB_PATH", "ldtvouchers.sqlite3")
).resolve()

print(f"Using database: {DB_PATH}")

app = FastAPI()

api = APIRouter(prefix="/api")

# Models


# VoucherState
# 0: registered
# 1: distributed
# 2: cashedin
# 3: expired
# 4: deactivated

# Severity
# 0: default
# 1: action
# 2: warning
# 3: error


class VoucherPatch(BaseModel):
    state: int  # TODO: use an enum
    # dummy: str


class VoucherBase(BaseModel):
    label: str  # TODO: remove, not needed anymore
    expiration_date: datetime.date  # TODO: handle expiration date
    value: int
    state: int  # TODO: use an enum


class Voucher(VoucherBase):
    id: str
    history: List[str]


class UserBase(BaseModel):
    name: str
    description: str
    ac_distribute: bool
    ac_cashin: bool


class User(UserBase):
    id: str


class Message(BaseModel):
    text: str
    severity: int = 0  # TODO: use an enum


class Action(BaseModel):
    url: str
    verb: str  # TODO: use an enum
    body: Union[dict, None]
    message: Union[Message, None]


class NextActions(BaseModel):
    scan: Union[Action, None]
    button: Union[Action, None]


class ActionResponse(BaseModel):
    user: Union[User, None]
    voucher: Union[Voucher, None]
    message_main: Union[Message, None]
    message_detail: Union[Message, None]
    next_actions: NextActions


# Dependency: get_con


def init_tables(con: Connection):
    with con:
        con.executescript(
            """
CREATE TABLE IF NOT EXISTS
users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    ac_distribute INTEGER DEFAULT 0,
    ac_cashin INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS
vouchers (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    expiration_date TEXT NOT NULL,
    value INTEGER NOT NULL,
    state INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS
history (
    date TEXT NOT NULL,
    userid TEXT NOT NULL,
    voucherid TEXT NOT NULL,
    state INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS
states (
	state	INTEGER,
	label	TEXT NOT NULL UNIQUE,
	PRIMARY KEY(state)
);

INSERT OR REPLACE INTO states
VALUES
    (0,'registered'),
    (1,'distributed'),
    (2,'cashedin'),
    (3,'expired'),
    (4,'deactivated');

CREATE VIEW IF NOT EXISTS
	v_history
AS
SELECT
	history.date as date,
	users.description as user,
	history.voucherid as voucher,
	states.label as state
FROM history
LEFT OUTER JOIN users ON history.userid = users.id
LEFT OUTER JOIN states ON history.state = states.state;

CREATE VIEW IF NOT EXISTS
    v_history_last_state
AS
SELECT
	MAX(history.date) as date,
	history.voucherid as voucherid,
	users.description as user,
	states.label as state
FROM
	history
LEFT OUTER JOIN users ON history.userid = users.id
LEFT OUTER JOIN states ON history.state = states.state
GROUP BY voucherid;

CREATE VIEW IF NOT EXISTS
    v_history_last_registered
AS
SELECT
	MAX(history.date) as date,
	history.voucherid as voucherid,
	users.description as user
FROM
	history
LEFT OUTER JOIN users
WHERE
	history.state = 0
	AND history.userid = users.id
GROUP BY voucherid;

CREATE VIEW IF NOT EXISTS
    v_history_last_distributed
AS
SELECT
	MAX(history.date) as date,
	history.voucherid as voucherid,
	users.description as user
FROM
	history
LEFT OUTER JOIN users
WHERE
	history.state = 1
	AND history.userid = users.id
GROUP BY voucherid;

CREATE VIEW IF NOT EXISTS
    v_history_last_cashedin
AS
SELECT
	MAX(history.date) as date,
	history.voucherid as voucherid,
	users.description as user
FROM
	history
LEFT OUTER JOIN users
WHERE
	history.state = 2
	AND history.userid = users.id
GROUP BY voucherid;

CREATE VIEW IF NOT EXISTS
    v_report
AS
SELECT
	vouchers.expiration_date as expiration_date,
	vouchers.id as voucher_id,
	vouchers.value as value_in_dollars,
	v_history_last_state.state as last_state,
	v_history_last_state.date as last_state_date,
	v_history_last_state.user as last_state_by,
	v_history_last_registered.date as last_registered_date,
	v_history_last_registered.user as last_registered_by,
	v_history_last_distributed.date as last_distributed_date,
	v_history_last_distributed.user as last_distributed_by,
	v_history_last_cashedin.date as last_cashedin_date,
	v_history_last_cashedin.user as last_cashedin_by
FROM
	vouchers
LEFT OUTER JOIN
    v_history_last_state ON vouchers.id = v_history_last_state.voucherid
LEFT OUTER JOIN
    v_history_last_registered ON vouchers.id = v_history_last_registered.voucherid
LEFT OUTER JOIN
    v_history_last_distributed ON vouchers.id = v_history_last_distributed.voucherid
LEFT OUTER JOIN
    v_history_last_cashedin ON vouchers.id = v_history_last_cashedin.voucherid;
"""
        )


def init_con(uri: str) -> Connection:
    # TODO: check_same_thread probably unsafe
    con = connect(uri, check_same_thread=False)
    con.row_factory = Row
    init_tables(con)
    return con


def get_con() -> Connection:
    con = init_con(DB_PATH)
    try:
        yield con
    finally:
        con.close()


# Initialize database file
next(get_con())

# Dependency: oauth2_scheme

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@api.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}


def decode_token(token):
    return {"name": "theName", "description": "theDescription", "id": "theId"}


async def get_current_user(
    con: Connection = Depends(get_con), token: str = Depends(oauth2_scheme)
) -> User:
    user = get_user(con, token)
    if user:
        return User(**user)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_voucher(
    voucherid: str, con: Connection = Depends(get_con)
) -> Voucher:
    voucher = get_voucher(con, voucherid)
    if voucher:
        return Voucher(**voucher)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


# Vouchers: DB


def get_voucher(con: Connection, voucherid: str) -> dict:
    cur = con.cursor()
    cur.execute("SELECT * FROM vouchers WHERE id=?", (voucherid,))
    voucher = cur.fetchone()
    if not voucher:
        return
    ret = dict(**voucher)
    ret["history"] = [
        _history_text(dict(**data)) for data in get_voucher_history(con, voucherid)
    ]
    return ret


def new_voucher_id(cur):  # TODO: type 
    cur.execute(
        """
        SELECT COUNT(*) FROM vouchers
        """
    )
    count, = cur.fetchone()
    return utils.new_voucher_id_string(count+1)


def new_voucher(con: Connection, user: User, voucher: VoucherBase) -> Voucher:
    values = voucher.dict()
    with con:
        cur = con.cursor()
        values["id"] = new_voucher_id(cur)
        cur.execute(
            """
            INSERT INTO history(date, userid, voucherid, state)
            VALUES(DATETIME('now'), :userid, :voucherid, :state)
            """,
            {"userid": user.id, "voucherid": values["id"], "state": voucher.state},
        )
        cur.execute(
            """
            INSERT INTO vouchers(id, label, expiration_date, value, state)
            VALUES(:id, :label, :expiration_date, :value, :state)
            """,
            values,
        )
    return get_voucher(con, values["id"])


def get_voucher_history(con: Connection, voucherid: str) -> dict:
    cur = con.cursor()
    cur.execute(
        """
        SELECT history.date, users.name, history.state
        FROM history
        INNER JOIN users ON history.userid = users.id
        INNER JOIN vouchers ON history.voucherid = vouchers.id
        WHERE history.voucherid = :voucherid
        ORDER BY
            history.date DESC,
            history.rowid DESC
        """,
        (voucherid,),
    )
    return cur.fetchall()


_HISTORY_MESSAGE = {0: "Registered by", 1: "Distributed by", 2: "Cashed-in by"}


def _build_last_history_message(con: Connection, voucherid: str) -> Union[str, None]:
    cur = con.cursor()
    cur.execute(
        """
        SELECT history.date, users.name, vouchers.state
        FROM history
        INNER JOIN users ON history.userid = users.id
        INNER JOIN vouchers ON history.voucherid = vouchers.id
        WHERE history.voucherid = :voucherid
        ORDER BY
            history.date DESC,
            history.rowid DESC
        LIMIT 1
        """,
        (voucherid,),
    )
    data = cur.fetchone()
    return _history_text(data) if data else None


def _history_text(data):
    by = _HISTORY_MESSAGE[data["state"]]
    return "{by} {name} {date}".format(by=by, **data)


# Used in tests
def _last_history_date(con: Connection, voucherid: str) -> str:
    cur = con.cursor()
    cur.execute(
        """
        SELECT MAX(date)
        FROM history
        WHERE voucherid = :voucherid;
        """,
        {"voucherid": voucherid},
    )
    return cur.fetchone()[0]


def patch_voucher(
    con: Connection, user: User, voucher: Voucher, patch: VoucherPatch
) -> None:
    # TODO: ensure user ACL
    with con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO history(date, userid, voucherid, state)
            VALUES(DATETIME('now'), :userid, :voucherid, :state)
            """,
            {"userid": user.id, "voucherid": voucher.id, "state": patch.state},
        )
        cur.execute(
            """
            UPDATE vouchers
            SET state = :state
            WHERE id = :id
            """,
            {"id": voucher.id, "state": patch.state},
        )


# Users: DBs


def get_user(con: Connection, userid: str) -> dict:
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (userid,))
    return cur.fetchone()


def new_user(con: Connection, user: UserBase) -> dict:
    values = user.dict()
    values["id"] = utils.new_user_id_string() # TODO: check for uniqueness in DB
    with con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO users(id, name, description, ac_distribute, ac_cashin)
            VALUES(:id, :name, :description, :ac_distribute, :ac_cashin)
            """,
            values,
        )
    return get_user(con, values["id"])


# Users: routes


@api.get("/users/{userid}", response_model=User)
async def users(userid: int, con: Connection = Depends(get_con)):
    user = read_user(con, userid)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@api.post("/users", response_model=User)
async def users(user: UserBase, con: Connection = Depends(get_con)):
    try:
        return create_user(con, user)
    except sqlite3.IntegrityError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )


def _noop(*_, **__):
    pass


_PATCH_VOUCHER_FUNCTIONS = {
    # ac_distribute, ac_cashin, cur_state, next_state
    (True, False, 0, 0): _noop,
    (True, False, 0, 1): patch_voucher,
    (True, False, 1, 0): patch_voucher,
    (True, False, 1, 1): _noop,
    (True, False, 2, 1): _noop,
    (False, True, 0, 2): _noop,
    (False, True, 1, 2): patch_voucher,
    (False, True, 2, 1): patch_voucher,
    (False, True, 2, 2): _noop,
}


@api.patch("/vouchers/{voucherid}", response_model=ActionResponse)
async def vouchers(
    patch: VoucherPatch,
    user: User = Depends(get_current_user),
    voucher: Voucher = Depends(get_current_voucher),
    con: Connection = Depends(get_con),
):
    try:
        patch_voucher_func = _PATCH_VOUCHER_FUNCTIONS[
            user.ac_distribute,
            user.ac_cashin,
            voucher.state,
            patch.state,
        ]
        patch_voucher_func(con, user, voucher, patch)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to perform this action.",
        )
    updated_voucher = Voucher(**get_voucher(con, voucher.id))
    message_builders = _MESSAGES[
        user.ac_distribute,
        user.ac_cashin,
        voucher.state,
        updated_voucher.state,
    ]
    message_main = message_builders["main"]
    message_detail = message_builders["detail"](con, updated_voucher)
    return ActionResponse(
        user=user,
        voucher=updated_voucher,
        message_main=message_main,
        message_detail=message_detail,
        next_actions=build_next_actions(user, voucher, patch.state),
    )


@api.get("/auth/{userid}", response_model=ActionResponse)
async def auth(userid: str, con: Connection = Depends(get_con)):
    user = get_user(con, userid)
    if user:
        user = User(**user)
        response = ActionResponse(
            user=user,
            next_actions=build_next_actions(user, None, None),
        )
        # TODO: fix the data model, this is ugly
        response.message_main = response.next_actions.scan.message
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid user")


@api.get("/auth", response_model=ActionResponse)
async def auth(user: User = Depends(get_current_user)):
    response = ActionResponse(
        user=user,
        next_actions=build_next_actions(user, None, None),
    )
    # TODO: fix the data model, this is ugly
    response.message_main = response.next_actions.scan.message
    return response


@dataclass
class Builder:
    scan: Callable
    button: Callable


def _build_scan_to_distribute_action() -> Action:
    return Action(
        url="/api/vouchers/{code}",
        verb="PATCH",
        body={"state": 1},  # distributed
        message=Message(text="Scan to distribute a voucher"),
    )


def _build_scan_to_cashin_action() -> Action:
    return Action(
        url="/api/vouchers/{code}",
        verb="PATCH",
        body={"state": 2},  # cashedin
        message=Message(text="Scan to cash a voucher in"),
    )


def _build_distribute_action(voucher: Voucher) -> Action:
    return Action(
        url=f"/api/vouchers/{voucher.id}",
        verb="PATCH",
        body={"state": 1},  # cashedin
        message=Message(text="Distribute", severity=1),
    )


def _build_cancel_distribute_action(voucher: Voucher) -> Action:
    return Action(
        url=f"/api/vouchers/{voucher.id}",
        verb="PATCH",
        body={"state": 0},  # cashedin
        message=Message(text="Cancel distribution", severity=2),
    )


def _build_cancel_cashin_action(voucher: Voucher) -> Action:
    return Action(
        url=f"/api/vouchers/{voucher.id}",
        verb="PATCH",
        body={"state": 1},  # distributed
        message=Message(text="Cancel cashing-in", severity=2),
    )


def _build_cashin_action(voucher: Voucher) -> Action:
    return Action(
        url=f"/api/vouchers/{voucher.id}",
        verb="PATCH",
        body={"state": 2},  # distributed
        message=Message(text="Cash-in", severity=1),
    )


def _build_none(*_, **__) -> None:
    return None


_BUILDERS = {  # (ac_distribute, ac_cashin, cur_state, next_state)
    (True, False, None, None): Builder(
        scan=_build_scan_to_distribute_action, button=_build_none
    ),
    (True, False, 0, 1): Builder(
        scan=_build_scan_to_distribute_action, button=_build_cancel_distribute_action
    ),
    (True, False, 1, 0): Builder(
        scan=_build_scan_to_distribute_action, button=_build_distribute_action
    ),
    (True, False, 1, 1): Builder(
        scan=_build_scan_to_distribute_action, button=_build_cancel_distribute_action
    ),
    (True, False, 2, 1): Builder(
        scan=_build_scan_to_distribute_action, button=_build_none
    ),
    (False, True, None, None): Builder(
        scan=_build_scan_to_cashin_action, button=_build_none
    ),
    (False, True, 0, 2): Builder(scan=_build_scan_to_cashin_action, button=_build_none),
    (False, True, 1, 2): Builder(
        scan=_build_scan_to_cashin_action, button=_build_cancel_cashin_action
    ),
    (False, True, 2, 1): Builder(
        scan=_build_scan_to_cashin_action, button=_build_cashin_action
    ),
    (False, True, 2, 2): Builder(
        scan=_build_scan_to_cashin_action, button=_build_cancel_cashin_action
    ),
}


def _last_state_message(con: Connection, voucher: Voucher) -> Message:
    return Message(text=_build_last_history_message(con, voucher.id), severity=0)


_MESSAGES = {
    (True, False, 0, 1): {
        "main": {"text": "Distributed", "severity": 1},
        "detail": _build_none,
    },
    (True, False, 1, 0): {
        "main": {"text": "Distribution cancelled", "severity": 2},
        "detail": _build_none,
    },
    (True, False, 1, 1): {
        "main": {"text": "Already distributed", "severity": 2},
        "detail": _last_state_message,
    },
    (True, False, 2, 2): {
        "main": {"text": "Already spent", "severity": 2},
        "detail": _last_state_message,
    },
    (False, True, 0, 0): {
        "main": {"text": "Not yet distributed", "severity": 2},
        "detail": _build_none,
    },
    (False, True, 1, 2): {
        "main": {"text": "Cashed-in", "severity": 1},
        "detail": _build_none,
    },
    (False, True, 2, 1): {
        "main": {"text": "Cashed-in cancelled", "severity": 2},
        "detail": _build_none,
    },
    (False, True, 2, 2): {
        "main": {"text": "Already cashed-in", "severity": 2},
        "detail": _last_state_message,
    },
}


def build_next_actions(
    user: User, voucher: Union[Voucher, None], next_state: Union[int, None]
) -> NextActions:
    cur_state = voucher.state if voucher else None
    builders = _BUILDERS[(user.ac_distribute, user.ac_cashin, cur_state, next_state)]
    return NextActions(scan=builders.scan(), button=builders.button(voucher))


# Start


@api.get("/start", response_model=ActionResponse)
async def start():
    return ActionResponse(
        message_main=Message(text="Not authentified", severity=2),
        message_detail=Message(text="Scan an authentification barcode", severity=0),
        next_actions=NextActions(scan=Action(url="/api/auth/{code}", verb="GET")),
    )


app.include_router(api)

# Static

if os.environ.get("LDTVOUCHERS_SERVE_STATIC_FILES", True):
    path = pathlib.Path(__file__).with_name("static")
    print(f"Serving static files: {path}")
    app.mount(
        "/",
        StaticFiles(directory=path, html=True, check_dir=True),
        name="static",
    )
