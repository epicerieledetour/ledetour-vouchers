import sys

from pydantic import BaseModel, Field

import app.utils.sql

from app.utils.models import build_crud

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


create, read, update, delete, history = build_crud(UserBase, User, "user", _SQLS)
