#!/usr/bin/env python

import argparse
import csv
import sqlite3
import sys

import shortuuid

parser = argparse.ArgumentParser(description="Number of shortuuids to generate")
parser.add_argument(
    "--db",
    type=str,
    default="ldtvouchers.sqlite3",
    help="DB to get the schema from",
)
parser.add_argument("table", type=str, help="Table to generate stub CVS for")
parser.add_argument("count", type=int, help="Number of lines to generate")

args = parser.parse_args()

conn = sqlite3.connect(args.db)
info = conn.execute(
    f"PRAGMA table_info({args.table})"
).fetchall()  # List[Tuple[index, name, type, ?, ?, ?]]
column_names = [col[1] for col in info]

w = csv.writer(sys.stdout, dialect="excel")
w.writerow(column_names)

for _ in range(args.count):
    row = [""] * len(column_names)
    row[column_names.index("id")] = shortuuid.uuid()
    w.writerow(row)

sys.stdout.flush
