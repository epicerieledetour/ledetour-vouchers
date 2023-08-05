import argparse
import sqlite3
import sys

from collections.abc import Iterable
from functools import wraps

from pydantic import BaseModel

import app.utils.sql

_PYDANTIC_TO_ARGPARSE_TYPES = {"integer": int, "string": str}


# Utils


def _add_ids_argument(parser) -> None:
    parser.add_argument("ids", nargs="+", help="User IDs to read")


def _add_arguments_model_arguments(Model: type[BaseModel], parser) -> None:
    for name, info in Model.schema()["properties"].items():
        # Usually id is a positional arg so we drop it from the optional args
        if name == "id":
            continue

        kwargs = {}

        description = info.get("description")
        if description:
            kwargs["help"] = description

        typ = _PYDANTIC_TO_ARGPARSE_TYPES.get(info.get("type"))
        if typ:
            kwargs["type"] = typ

        parser.add_argument(f"--{name}", **kwargs)


def _build_model_from_args(
    Model: type[BaseModel], args: argparse.Namespace
) -> BaseModel:
    fields = {}
    for name in Model.schema()["properties"]:
        if hasattr(args, name):
            fields[name] = getattr(args, name)
    return Model(**fields)


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


def _model(model_class):
    def decorator(func):
        @wraps(func)
        def wrap(parser_args, *args, **kwargs):
            model = _build_model_from_args(model_class, parser_args)
            return func(parser_args, *args, model=model, **kwargs)

        return wrap

    return decorator


def _print_json(func):
    def wrap(*args, **kwargs):
        for model in func(*args, **kwargs):
            print(model.json())

    return wrap


def add_crud(subparsers, Base: type[BaseModel], Entity: type[BaseModel], models):
    # Create

    @_conn
    @_model(Base)
    def _create(
        args: argparse.Namespace, conn: sqlite3.Connection, model: Base
    ) -> Entity:
        for entity in models.create(conn, [model]):
            print(entity.id)

    parser = subparsers.add_parser("create")
    _add_arguments_model_arguments(Base, parser)
    parser.set_defaults(command=_create)

    # Read

    @_conn
    @_print_json
    def _read(args: argparse.Namespace, conn: sqlite3.Connection) -> Iterable[Entity]:
        try:
            yield from models.read(conn, args.ids)
        except ValueError as err:
            sys.exit(err)

    parser = subparsers.add_parser("read")
    _add_ids_argument(parser)
    parser.set_defaults(command=_read)

    # List

    @_conn
    @_print_json
    def _list(args: argparse.Namespace, conn: sqlite3.Connection) -> Iterable[Entity]:
        yield from models.read(conn)

    parser = subparsers.add_parser("list")
    parser.set_defaults(command=_list)

    # Update

    @_conn
    @_model(Entity)
    def _update(
        args: argparse.Namespace, conn: sqlite3.Connection, model: Entity
    ) -> None:
        models.update(conn, [model])

    parser = subparsers.add_parser("update")
    parser.add_argument("id", help="Entity ID")
    _add_arguments_model_arguments(Entity, parser)
    parser.set_defaults(command=_update)

    # Delete

    @_conn
    def _delete(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
        with conn:
            users = models.read(conn, args.ids)
            models.delete(conn, users)

    parser = subparsers.add_parser("delete")
    _add_ids_argument(parser)
    parser.set_defaults(command=_delete)

    # History

    @_conn
    @_print_json
    def _history(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
        return models.history_users(conn, args.ids)

    parser = subparsers.add_parser("history")
    _add_ids_argument(parser)
    parser.set_defaults(command=_history)
