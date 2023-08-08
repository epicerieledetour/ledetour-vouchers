import argparse
import sqlite3
import sys

from app.corecli.cli import subparsers

from app.corecli.utils import add_crud, _add_id_argument, _conn

from . import models


@_conn
def _export(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    models.export_csv(conn, args.id, args.path)


@_conn
def _import(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    models.import_csv(conn, args.id, args.path)


subparsers = subparsers.add_parser("emissions").add_subparsers()

add_crud(subparsers, models.EmissionBase, models.Emission, models)

parser = subparsers.add_parser("export")
_add_id_argument(parser)
parser.add_argument(
    "path", type=argparse.FileType("w"), help="The path to the CSV file to write"
)
parser.set_defaults(command=_export)

parser = subparsers.add_parser("import")
_add_id_argument(parser)
parser.add_argument(
    "path", type=argparse.FileType("r"), help="The path to the CSV file to read"
)
parser.set_defaults(command=_import)
