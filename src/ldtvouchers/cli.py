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
    if hasattr(ns, "command"):
        ns.command(ns)


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
