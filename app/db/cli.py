import argparse
import logging

from sqlite3 import Connection

import app

from app.corecli.cli import parser, subparsers
from app.utils import sql


def _init(args: argparse.Namespace) -> None:
    conn = sql.get_connection(args.db)
    init(conn)
    conn.close()


def init(conn: Connection) -> None:
    with conn:
        for module in app.modules:
            sqls = sql.get_module_queries(module)
            if hasattr(sqls, "init"):
                logging.debug(f"Executing {module.__name__} init.sql")
                conn.executescript(sqls.init)


db_parser = subparsers.add_parser("db")

db_subparsers = db_parser.add_subparsers()

init_parser = db_subparsers.add_parser("init")
init_parser.set_defaults(command=_init)
