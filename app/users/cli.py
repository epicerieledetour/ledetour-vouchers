import argparse
import sqlite3
import sys

from collections.abc import Iterable
from functools import wraps

from pydantic import BaseModel

import app.utils.sql

from app.corecli.cli import subparsers

from . import models

_PYDANTIC_TO_ARGPARSE_TYPES = {"integer": int, "string": str}


# Utils


def _add_ids_argument(parser) -> None:
    parser.add_argument("ids", nargs="+", help="User IDs to read")


def _add_arguments_model_arguments(model: BaseModel, parser) -> None:
    for name, info in model.schema()["properties"].items():
        kwargs = {}

        description = info.get("description")
        if description:
            kwargs["help"] = description

        typ = _PYDANTIC_TO_ARGPARSE_TYPES.get(info.get("type"))
        if typ:
            kwargs["type"] = typ

        parser.add_argument(f"--{name}", **kwargs)


def _build_user_from_args(model: BaseModel, args: argparse.Namespace) -> models.User:
    fields = {}
    for name in model.schema()["properties"]:
        if hasattr(args, name):
            fields[name] = getattr(args, name)
    return model(**fields)


def _get_argument(func, name, *args, **kwargs):
    bound_signature = inspect.signature(func).bind(*args, **kwargs)
    return bound_signature.arguments[name]


# Decorators


def _conn(func):
    @wraps(func)
    def wrap(parser_args, *args, **kwargs):
        conn = conn = app.utils.sql.get_connection(parser_args.db)
        return func(parser_args, *args, conn=conn, **kwargs)

    return wrap


def _user(func):
    @wraps(func)
    def wrap(parser_args, *args, **kwargs):
        user = _build_user_from_args(models.User, parser_args)
        return func(parser_args, *args, user=user, **kwargs)

    return wrap


def _print_json(func):
    def wrap(*args, **kwargs):
        for model in func(*args, **kwargs):
            print(model.json())

    return wrap


# Command implementations


@_conn
def _create_user(args: argparse.Namespace, conn: sqlite3.Connection) -> models.User:
    fields = {}
    for name in models.UserBase.schema()["properties"]:
        if hasattr(args, name):
            fields[name] = getattr(args, name)

    users = models.create_users(conn, [models.UserBase(**fields)])
    for user in users:
        print(user.id)


@_conn
@_print_json
def _read_users(
    args: argparse.Namespace, conn: sqlite3.Connection
) -> Iterable[models.User]:
    try:
        yield from models.read_users(conn, args.ids)
    except ValueError as err:
        sys.exit(err)


@_conn
@_print_json
def _list_users(
    args: argparse.Namespace, conn: sqlite3.Connection
) -> Iterable[models.User]:
    yield from models.read_users(conn)


@_conn
@_user
def _update_user(
    args: argparse.Namespace, conn: sqlite3.Connection, user: models.User
) -> None:
    models.update_users(conn, [user])


@_conn
def _delete_users(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    with conn:
        users = models.read_users(conn, args.ids)
        models.delete_users(conn, users)


# Parsers definition

parser = subparsers.add_parser("users")

subparsers = parser.add_subparsers()

# Create

create_parser = subparsers.add_parser("create")
_add_arguments_model_arguments(models.UserBase, create_parser)
create_parser.set_defaults(command=_create_user)

# Read

read_parser = subparsers.add_parser("read")
_add_ids_argument(read_parser)
read_parser.set_defaults(command=_read_users)

# List

list_parser = subparsers.add_parser("list")
list_parser.set_defaults(command=_list_users)

# Update

update_parser = subparsers.add_parser("update")
update_parser.add_argument("id", help="User ID")
_add_arguments_model_arguments(models.User, update_parser)
update_parser.set_defaults(command=_update_user)

# Delete

delete_parser = subparsers.add_parser("delete")
_add_ids_argument(delete_parser)
delete_parser.set_defaults(command=_delete_users)
