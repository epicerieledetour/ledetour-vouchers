# TODO: reactivate mypy
# type: ignore
import argparse
import contextlib
import datetime
import functools
import pathlib
import sqlite3
import sys
from collections.abc import Callable, Iterable, Sequence
from types import NoneType, UnionType
from typing import Any, Text

import pydantic

from . import db, models


def _connect(func):
    @functools.wraps(func)
    def wrap(ns: argparse.Namespace, *args, **kwargs):
        conn = db.connect(ns.db)

        with contextlib.closing(conn):
            with conn:
                try:
                    func(ns, conn, *args, **kwargs)
                except db.UnknownId as err:
                    sys.exit(err)
                except Exception:
                    raise

    return wrap


def _json(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        ret = func(*args, **kwargs)
        print(ret.json())

    return wrap


def _model(arg_name: str, Model: type[pydantic.BaseModel]):
    def decorator(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            ns = args[0]

            # model_args = dict((name, getattr(ns, name)) for name in Model.model_fields)
            model_args = {}
            for name in Model.model_fields:
                if val := getattr(ns, name, None):
                    model_args[name] = val

            try:
                model = Model(**model_args)
            except:
                raise

            kwargs[arg_name] = model

            return func(*args, **kwargs)

        return wrap

    return decorator


def _add_id_argument(parser, model) -> None:
    parser.add_argument(
        "id", type=int, help=f"The {model.model_json_schema()['title'].lower()} ID"
    )


@_connect
def _db_init(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    db.initdb(conn)


# Users


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
def _users_list(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    for user in db.list_users(conn):
        print(f"{user.userid} {user.label}")


@_connect
@_model("user", models.User)
@_json
def _users_update(
    args: argparse.Namespace, conn: sqlite3.Connection, user: models.User
) -> None:
    return db.update_user(conn, user)


@_connect
def _users_delete(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    db.delete_user(conn, args.id)


# Emissions


@_connect
@_model("emission", models.EmissionBase)
@_json
def _emissions_create(
    args: argparse.Namespace, conn: sqlite3.Connection, emission: models.EmissionBase
) -> models.Emission:
    return db.create_emission(conn, emission)


@_connect
@_json
def _emissions_read(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    return db.read_emission(conn, args.id)


@_connect
def _emissions_list(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    for emission in db.list_emissions(conn):
        print(f"{emission.emissionid} {emission.label}")


@_connect
@_model("emission", models.Emission)
@_json
def _emissions_update(
    args: argparse.Namespace, conn: sqlite3.Connection, emission: models.Emission
) -> None:
    return db.update_emission(conn, emission)


@_connect
def _emissions_delete(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    db.delete_emission(conn, args.id)


# Utils

_ARG_DEFAULT_FOR_TYPE = {datetime.datetime: datetime.datetime.fromisoformat}


def _add_model_schema_as_arguments(
    model: type[pydantic.BaseModel], parser: argparse.ArgumentParser
) -> None:
    def _is_atomic_type(field: pydantic.Field) -> bool:
        default = field.get_default()
        try:
            if isinstance(default, str):
                return True
        except:
            raise
        return not isinstance(default, Iterable)
        # typ = field.annotation

        # for name in ("__origin__", "__supertype__"):
        #     if hasattr(typ, name):
        #         typ = getattr(typ, name)
        #         break

        # try:
        #     if issubclass(typ, str):
        #         return True
        # except:
        #     raise

        # return not issubclass(typ, Iterable)

    def _type(field: pydantic.Field) -> Callable[[str], Any] | None:
        typ = field.annotation

        if isinstance(typ, UnionType):
            types = set(typ.__args__)
            if len(types) == 2 and NoneType in types:
                types.remove(NoneType)
                typ = types.pop()

        if typ in _ARG_DEFAULT_FOR_TYPE:
            return _ARG_DEFAULT_FOR_TYPE[typ]

        return typ

    fields = (
        (name, field)
        for name, field in model.model_fields.items()
        # Not taking compound fields, like a list of vouchers
        if _is_atomic_type(field)
    )

    fields = list(fields)

    for name, field in fields:
        args = (name if field.is_required() else f"--{name}",)

        kwargs = {}
        if typ := _type(field):
            kwargs["type"] = typ

        if description := field.description:
            kwargs["help"] = description

        try:
            parser.add_argument(*args, **kwargs)
        except:
            raise


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

    par = sub.add_parser("list")
    par.set_defaults(command=_users_list)

    par = sub.add_parser("update")
    _add_model_schema_as_arguments(models.User, par)
    par.set_defaults(command=_users_update)

    par = sub.add_parser("delete")
    _add_id_argument(par, models.User)
    par.set_defaults(command=_users_delete)

    # emissions

    sub = subparsers.add_parser("emissions").add_subparsers()

    par = sub.add_parser("create")
    _add_model_schema_as_arguments(models.EmissionBase, par)
    par.set_defaults(command=_emissions_create)

    par = sub.add_parser("read")
    _add_id_argument(par, models.Emission)
    par.set_defaults(command=_emissions_read)

    par = sub.add_parser("list")
    par.set_defaults(command=_emissions_list)

    par = sub.add_parser("update")
    _add_model_schema_as_arguments(models.Emission, par)
    par.set_defaults(command=_emissions_update)

    par = sub.add_parser("delete")
    _add_id_argument(par, models.Emission)
    par.set_defaults(command=_emissions_delete)

    # All done !

    return parser
