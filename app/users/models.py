import sys

from collections.abc import Iterable
from sqlite3 import Connection

from pydantic import BaseModel

import app.events.models
import app.utils

import app.utils.sql

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])


class UserBase(BaseModel):
    label: str
    description: str | None


class User(UserBase):
    id: str
    deleted: bool | None


def create_users(conn: Connection, users: Iterable[UserBase]) -> Iterable[User]:
    def events():
        for user, userid in zip(users, ids):
            # Creation event

            yield app.events.models.CreateEvent(elemid=userid)

            # Attribute setting events

            data = user.dict()
            data["deleted"] = False

            for field, value in data.items():
                yield app.events.models.UpdateEvent(
                    elemid=userid, field=field, value=value
                )

    ids = [app.utils.makeid("user") for _ in users]

    app.events.models.append_events(conn, events())
    return read_users(conn, ids)


def _make_ids_string_usable_in_where_id_in_clause(
    ids: Iterable[str] | None,
) -> str | None:
    if not ids:
        return None

    ids_tuple = tuple(ids)

    if not ids_tuple:
        return None

    ids_tuple = (f"'{id_str}'" for id_str in ids_tuple)
    print(type(ids_tuple))
    return ", ".join(ids_tuple)


def read_users(conn: Connection, ids: Iterable[str] | None) -> Iterable[User]:
    ids_string = _make_ids_string_usable_in_where_id_in_clause(ids)
    query = _SQLS.read.format(ids_string=ids_string) if ids_string else _SQLS.list
    res = conn.execute(query)
    for user in res:
        yield User(**user)
