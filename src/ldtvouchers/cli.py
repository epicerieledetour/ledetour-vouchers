# TODO: reactivate mypy
# type: ignore

import argparse
import contextlib
import pathlib
import sqlite3
from collections.abc import Sequence
from typing import Text

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


def _add_id_argument(parser, model) -> None:
    parser.add_argument(
        "id", help=f"The {model.model_json_schema()['title'].lower()} ID"
    )


@_connect
def _db_init(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    db.initdb(conn)


@_connect
@_json
def _users_create(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    return db.create_user(conn, models.UserBase())


@_connect
@_json
def _users_read(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    return db.read_user(conn, args.id)


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
    par.set_defaults(command=_users_create)

    par = sub.add_parser("read")
    _add_id_argument(par, models.User)
    par.set_defaults(command=_users_read)

    # All done !

    return parser
