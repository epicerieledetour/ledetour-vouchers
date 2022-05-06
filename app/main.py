import sqlite3
from sqlite3 import connect, Connection, Row

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

DB_PATH = "db.sqlite3"

app = FastAPI()


def init_con(con: Connection):
    with con:
        con.executescript(
            """
CREATE TABLE IF NOT EXISTS
users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
)
"""
        )


def get_con() -> Connection:
    # TODO: check_same_thread probably unsafe
    con = connect(DB_PATH, check_same_thread=False)
    con.row_factory = Row
    init_con(con)
    try:
        yield con
    finally:
        con.close()


class UserBase(BaseModel):
    name: str
    description: str


class User(UserBase):
    id: str


def read_user(con: Connection, userid: int) -> dict:
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (userid,))
    return cur.fetchone()


def create_user(con: Connection, user: UserBase) -> User:
    with con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users(name, description) VALUES(:name, :description)",
            user.dict(),
        )
    return read_user(con, cur.lastrowid)


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


# HTML /: main page
# JSON /{userid}: returns info about an user
# HTML /{userid}: logged user main page
# JSON /{userid}/{voucherid}: returns the state of a voucher for an user
# HTML /{userid}/{voucherid}: display the state of a voucher for an user
