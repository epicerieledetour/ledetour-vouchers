# TODO: reactivate mypy
# type: ignore
import argparse
import contextlib
import functools
import pathlib
import sqlite3
from collections.abc import Sequence
from typing import Text

import pydantic

from . import db, models


def _connect(func):
    def wrap(ns: argparse.Namespace, *args, **kwargs):
        with contextlib.closing(db.connect(ns.db)) as conn:
            func(ns, conn, *args, **kwargs)

    return wrap


def _json(func):
    def wrap(*args, **kwargs):
        ret = func(*args, **kwargs)
        print(ret.json())

    return wrap


def _model(arg_name: str, Model: type[pydantic.BaseModel]):
    def decorator(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            ns = args[0]

            model_args = dict((name, getattr(ns, name)) for name in Model.model_fields)
            model = Model(**model_args)

            kwargs[arg_name] = model

            return func(*args, **kwargs)

        return wrap

    return decorator


def _add_id_argument(parser, model) -> None:
    parser.add_argument(
        "id", help=f"The {model.model_json_schema()['title'].lower()} ID"
    )


@_connect
def _db_init(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    db.initdb(conn)


@_connect
@_model("user", models.UserBase)
@_json
def _users_create(
    args: argparse.Namespace, conn: sqlite3.Connection, user: models.UserBase
) -> None:
    return db.create_user(conn, user)


@_connect
@_json
def _users_read(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    return db.read_user(conn, args.id)


@_connect
@_model("user", models.User)
@_json
def _users_update(
    args: argparse.Namespace, conn: sqlite3.Connection, user: models.User
) -> None:
    return db.update_user(conn, user)


def _add_model_schema_as_arguments(
    model: type[pydantic.BaseModel], parser: argparse.ArgumentParser
) -> None:
    for name, field in model.model_fields.items():
        parser.add_argument(
            name if field.is_required() else f"--{name}",
            type=field.annotation,
            default=field.get_default(),
            help=field.description,
        )


def parse_args(args: Sequence[Text] | None = None) -> None:
    parser = _build_parser()
    ns = parser.parse_args(args)

    # TODO: remove pragma no cover
    # For some reason the next two lines are not marked as
    # as coverage during testing, although executed
    if hasattr(ns, "command"):  # pragma: no cover
        ns.command(ns)  # pragma: no cover
    else:  # pragma: no cover
        parser.print_usage()  # pragma: no cover


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ldtvouchers", description="Command line interface for ldtvouchers"
    )

    parser.add_argument(
        "--db",
        default="db.sqlite3",
        type=pathlib.Path,
        help="Path to the database file",
    )

    subparsers = parser.add_subparsers()

    # db

    sub = subparsers.add_parser("db").add_subparsers()

    par = sub.add_parser("init")
    par.set_defaults(command=_db_init)

    # users

    sub = subparsers.add_parser("users").add_subparsers()

    par = sub.add_parser("create")
    _add_model_schema_as_arguments(models.UserBase, par)
    par.set_defaults(command=_users_create)

    par = sub.add_parser("read")
    _add_id_argument(par, models.User)
    par.set_defaults(command=_users_read)

    par = sub.add_parser("update")
    _add_model_schema_as_arguments(models.User, par)
    par.set_defaults(command=_users_update)

    # All done !

    return parser
