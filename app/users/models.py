import sys

from collections.abc import Iterable
from sqlite3 import Connection

from pydantic import BaseModel, Field

import app.events.models
import app.utils

import app.utils.sql

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])


class UserBase(BaseModel):
    label: str | None = Field(default=None, description="A short user name, ie. LDT")
    description: str | None = Field(
        default=None,
        description="A longer, explicit user description, ie. 'Le Détour Cashier #1'",
    )


class User(UserBase):
    id: str
    deleted: bool | None = (
        None  # TODO: something is wrong, the sql queries expect a string
    )


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
) -> tuple[tuple[str], str | None]:
    if not ids:
        return tuple(), None

    ids_tuple = tuple(ids)

    if not ids_tuple:
        return tuple(), None

    id_strings = (f"'{id_str}'" for id_str in ids_tuple)

    return ids_tuple, ", ".join(id_strings)


def read_users(conn: Connection, ids: Iterable[str] | None = None) -> Iterable[User]:
    # TODO: perf, lot of buffering and traversals here
    ids, ids_string = _make_ids_string_usable_in_where_id_in_clause(ids)
    query = _SQLS.read.format(ids_string=ids_string) if ids_string else _SQLS.list
    res = conn.execute(query)
    users = tuple(User(**user) for user in res)

    diff_ids = set(ids) - {user.id for user in users}

    if diff_ids:
        raise ValueError(f"Trying to fetch unknown ids: {', '.join(diff_ids)}")

    return users


def _diff_models(base: BaseModel, updated: BaseModel) -> dict:
    base = base.dict()
    updated = updated.dict()
    return {k: updated[k] for k in base if k in updated and base[k] != updated[k]}


def update_users(conn: Connection, updated_users: Iterable[User]) -> None:
    def events():
        diff_dicts = tuple(
            _diff_models(current, updated)
            for (current, updated) in zip(current_users, updated_users)
        )

        for userid, diff_dict in zip(ids, diff_dicts):
            for field, value in diff_dict.items():
                if value is not None:
                    yield app.events.models.UpdateEvent(
                        elemid=userid, field=field, value=value
                    )

    updated_users = tuple(updated_users)

    ids = tuple(user.id for user in updated_users)

    with conn:
        current_users = read_users(conn, ids)
        events = tuple(events())
        app.events.models.append_events(conn, events)


def delete_users(conn: Connection, users: Iterable[User]) -> None:
    users = (user.copy(update={"deleted": "1"}) for user in users)
    update_users(conn, users)
