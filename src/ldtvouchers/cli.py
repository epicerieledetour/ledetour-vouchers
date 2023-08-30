import argparse
import contextlib
import pathlib
from collections.abc import Sequence
from typing import Text

from . import db


def _init(args: argparse.Namespace) -> None:
    conn = db.connect(args.db)
    with contextlib.closing(conn):
        db.initdb(conn)


def parse_args(args: Sequence[Text] | None = None) -> None:
    ns = _build_parser().parse_args(args)

    # TODO: remove pragma no cover
    # For some reason the next two lines are not marked as
    # as coverage during testing, although executed
    if hasattr(ns, "command"):  # pragma: no cover
        ns.command(ns)  # pragma: no cover


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
    par.set_defaults(command=_init)

    # All done !

    return parser
