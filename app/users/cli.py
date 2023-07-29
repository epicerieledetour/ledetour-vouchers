import argparse

from collections.abc import Iterable

from pydantic import BaseModel

import app.utils.sql

from app.corecli.cli import subparsers

from . import models

_PYDANTIC_TO_ARGPARSE_TYPES = {"integer": int, "string": str}


def _create_user(args: argparse.Namespace) -> models.User:
    conn = app.utils.sql.get_connection(args.db)

    fields = {}
    for name in models.UserBase.schema()["properties"]:
        if hasattr(args, name):
            fields[name] = getattr(args, name)

    users = models.create_users(conn, [models.UserBase(**fields)])
    for user in users:
        print(user.id)


def _print_json(func):
    def wrap(*args, **kwargs):
        for model in func(*args, **kwargs):
            print(model.json())

    return wrap


@_print_json
def _read_users(args: argparse.Namespace) -> models.User:
    conn = app.utils.sql.get_connection(args.db)
    return models.read_users(conn, args.ids)


@_print_json
def _list_users(args: argparse.Namespace) -> models.User:
    conn = app.utils.sql.get_connection(args.db)
    return models.read_users(conn)


parser = subparsers.add_parser("users")

subparsers = parser.add_subparsers()

# Create

create_parser = subparsers.add_parser("create")

for name, info in models.UserBase.schema()["properties"].items():
    kwargs = {}

    description = info.get("description")
    if description:
        kwargs["help"] = description

    typ = _PYDANTIC_TO_ARGPARSE_TYPES.get(info.get("type"))
    if typ:
        kwargs["type"] = typ

    create_parser.add_argument(f"--{name}", **kwargs)

create_parser.set_defaults(command=_create_user)


# Read

read_parser = subparsers.add_parser("read")
read_parser.add_argument("ids", nargs="+", help="User IDs to read")
read_parser.set_defaults(command=_read_users)


# List

list_parser = subparsers.add_parser("list")
list_parser.set_defaults(command=_list_users)
