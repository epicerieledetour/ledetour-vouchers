import argparse
import pathlib

parser = argparse.ArgumentParser(
    prog="ldtvouchers", description="Command line interface for ldtvouchers"
)

parser.add_argument(
    "--db", default="db.sqlite3", type=pathlib.Path, help="Path to the database file"
)

subparsers = parser.add_subparsers()
