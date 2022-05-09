from typing import Dict

import shortuuid

import sqlite3
from sqlite3 import connect, Connection, Row

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

DB_PATH = "db.sqlite3"

app = FastAPI()


# Models


# VoucherState
# 0: registered
# 1: distributed
# 2: cashedin
# 3: expired
# 4: desactivated

# Severity
# 0: default
# 1: action
# 2: warning
# 3: error


class UserBase(BaseModel):
    name: str
    description: str
    ac_distribute: bool
    ac_cashin: bool


class User(UserBase):
    id: str


class Message(UserBase):
    text: str
    severity: int  # TODO: use an enum


class Action(BaseModel):
    url: str
    verb: str  # TODO: use an enum
    body: dict
    message: Message | None


class NextActions(BaseModel):
    scan: Action | None
    button: Action | None


class ActionResponse(BaseModel):
    user: User
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
"""
        )


def init_con(uri: str) -> Connection:
    # TODO: check_same_thread probably unsafe
    con = connect(uri, check_same_thread=False)
    con.row_factory = Row
    init_tables(con)
    return con


def get_con() -> Connection:
    con = init_cont(DB_PATH)
    try:
        yield con
    finally:
        con.close()


# Dependency: oauth2_scheme

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}


def decode_token(token):
    return {"name": "theName", "description": "theDescription", "id": "theId"}


async def get_current_user(
    con: Connection = Depends(get_con), token: str = Depends(oauth2_scheme)
) -> User:
    return get_user(con, token)


# Users: DB


def get_user(con: Connection, userid: str) -> dict:
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (userid,))
    return cur.fetchone()


def new_user(con: Connection, user: UserBase) -> dict:
    values = user.dict()
    values["id"] = shortuuid.uuid()  # TODO: check for uniqueness in DB
    with con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO users(id, name, description, ac_distribute, ac_cashin)
            VALUES(:id, :name, :description, :ac_distribute, :ac_cashin)
            """,
            values,
        )
    return get_user(con, cur.lastrowid)


# Users: routes


@app.get("/users/{userid}", response_model=User)
async def users(userid: int, con: Connection = Depends(get_con)):
    if user := read_user(con, userid):
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@app.post("/users", response_model=User)
async def users(user: UserBase, con: Connection = Depends(get_con)):
    try:
        return create_user(con, user)
    except sqlite3.IntegrityError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )


@app.get("/auth", response_model=ActionResponse)
async def auth(user: User = Depends(get_current_user)):
    if user:
        return ActionResponse(
            user=User(**user),
            next_actions=build_next_actions(user),
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def build_next_actions(user: User) -> Dict[str, Action]:
    if user["ac_distribute"]:
        return NextActions(
            scan=Action(
                url="/vouchers/{voucherid}",
                verb="PATCH",
                body={"state": 1},  # distributed
                message=None,
            )
        )

    if user["ac_cashin"]:
        return NextActions(
            scan=Action(
                url="/vouchers/{voucherid}",
                verb="PATCH",
                body={"state": 2},  # cashedin
                message=None,
            )
        )
