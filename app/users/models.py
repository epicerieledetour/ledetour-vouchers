from sqlite3 import Connection

from pydantic import BaseModel

import app.events.models
import app.utils


class UserBase(BaseModel):
    label: str
    description: str | None


class User(UserBase):
    id: str


def create_user(conn: Connection, user: UserBase) -> User:
    elemid = app.utils.makeid("user")
    events = [app.events.models.CreateEvent(elemid=elemid)]
    app.events.models.append_events(conn, events)
    return User(id="theId", label="theLabel", description="theDescription")
