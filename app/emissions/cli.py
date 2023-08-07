import argparse
import csv
import sqlite3
import sys

from app.corecli.cli import subparsers

from app.corecli.utils import add_crud, _add_ids_argument, _conn

from . import models


@_conn
def _export(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    writer = csv.DictWriter(
        args.path,
        fieldnames=["voucher_index", "voucher_value_CAD", "distributor_label"],
    )
    writer.writeheader()


subparsers = subparsers.add_parser("emissions").add_subparsers()

add_crud(subparsers, models.EmissionBase, models.Emission, models)

parser = subparsers.add_parser("export")
_add_ids_argument(parser)
parser.add_argument(
    "path", type=argparse.FileType("w"), help="The path to the CSV file to write"
)
parser.set_defaults(command=_export)
