import argparse
import logging

import app

from app.corecli.cli import parser, subparsers
from app.utils import sql

from . import init


def _init(args: argparse.Namespace) -> None:
    conn = sql.get_connection(args.db)
    init(conn)
    conn.close()


db_parser = subparsers.add_parser("db")

db_subparsers = db_parser.add_subparsers()

init_parser = db_subparsers.add_parser("init")
init_parser.set_defaults(command=_init)
