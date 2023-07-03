import dataclasses
import sys

from collections.abc import Iterable
from datetime import datetime
from sqlite3 import Connection
from typing import Any

from pydantic import BaseModel

import app.utils.sql


class _EventBase(BaseModel):
    commandid: str
    elemid: str


class CreateEvent(_EventBase):
    def __init__(self, elemid: str) -> None:
        super().__init__(commandid="event_create", elemid=elemid)


class _EventIn(_EventBase):
    bundleid: str
    field: str = ""
    value: Any = ""


class Event(_EventIn):
    id: str
    timestamp_utc: datetime
    statusid: str


def _append_event_create(conn: Connection, event: _EventIn) -> None:
    sqls = app.utils.sql.get_module_queries(sys.modules[__name__])
    parameters = event.dict()
    parameters["id"] = app.utils.makeid("event")
    conn.execute(sqls.create, parameters)


def _append_invalid_event(conn: Connection, event: _EventIn) -> None:
    pass


_EVENT_DISPATCH = {
    "event_create": _append_event_create,
    # "event_delete": _append_event_delete,
    # "event_read": _append_event_read,
    # "event_update": _append_event_update,
}


def append_events(conn: Connection, events: Iterable[_EventBase]) -> list[Event]:
    ret = []

    bundleid = app.utils.makeid("bundle")

    with conn:
        for src_event in events:
            event_in = _EventIn(bundleid=bundleid, **src_event.dict())
            append_event = _EVENT_DISPATCH.get(
                event_in.commandid, _append_invalid_event
            )
            append_event(conn, event_in)

    return ret
