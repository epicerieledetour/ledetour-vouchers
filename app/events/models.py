import dataclasses
import sys

from collections.abc import Iterable
from datetime import datetime
from sqlite3 import Connection
from typing import Any

from pydantic import BaseModel

import app.utils.sql

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])

# TODO: how to avoid duplication from init.sql ?

_EVENT_CREATE = "event_create"
_EVENT_READ = "event_read"
_EVENT_UPDATE = "event_update"
_EVENT_DELETE = "event_delete"


# TODO: how to avoid duplication from init.sql ?

_STATUS_OK = "status_ok"
_STATUS_INVALID_ELEMENT = "status_invalid_element"
_STATUS_INVALID_COMMAND = "status_invalid_command"


class _EventBase(BaseModel):
    commandid: str
    elemid: str  # TODO: rename this attribute to entityid, to respect EAV naming convention
    field: str | None  # TODO: rename this attribute to attributeid, to respect EAV naming convention
    value: Any | None


class CreateEvent(_EventBase):
    def __init__(self, elemid: str) -> None:
        super().__init__(commandid=_EVENT_CREATE, elemid=elemid)


class UpdateEvent(_EventBase):
    def __init__(self, elemid: str, field: str, value: str) -> None:
        super().__init__(
            commandid=_EVENT_UPDATE, elemid=elemid, field=field, value=value
        )


class _EventIn(_EventBase):
    bundleid: str


class Event(_EventIn):
    id: str
    timestamp_utc: datetime
    statusid: str


class _StatusBase(BaseModel):
    statusid: str


class StatusOK(_StatusBase):
    def __init__(self) -> None:
        super().__init__(statusid=_STATUS_OK)


class StatusInvalidElement(_StatusBase):
    def __init__(self) -> None:
        super().__init__(statusid=_STATUS_INVALID_ELEMENT)


class StatusInvalidCommand(_StatusBase):
    def __init__(self) -> None:
        super().__init__(statusid=_STATUS_INVALID_COMMAND)


def _append_event_create(conn: Connection, event: _EventIn) -> None:
    parameters = event.dict()
    parameters["id"] = app.utils.makeid("event")
    conn.execute(_SQLS.create, parameters)


def _append_invalid_event(conn: Connection, event: _EventIn) -> None:
    pass


# TODO: remove _EVENT_DISPATCH, this is not useful

_EVENT_DISPATCH = {
    _EVENT_CREATE: _append_event_create,
    # _EVENT_READ: _append_event_read,
    _EVENT_UPDATE: _append_event_create,
    # _EVENT_DELETE: _append_event_delete,
}


def append_events(conn: Connection, events: Iterable[_EventBase]) -> list[Event]:
    ret = []

    bundleid = app.utils.makeid("bundle")

    # TODO: make this a single sqlite transaction

    with conn:
        for src_event in events:
            event_in = _EventIn(bundleid=bundleid, **src_event.dict())
            append_event = _EVENT_DISPATCH.get(
                event_in.commandid, _append_invalid_event
            )
            append_event(conn, event_in)

    return ret


def read_events(conn: Connection) -> list[Event]:
    res = conn.execute(_SQLS.read)
    evs = res.fetchall()
    return [Event(**ev) for ev in evs]
