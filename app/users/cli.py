import argparse

import app.utils.sql

from app.corecli.cli import subparsers

from .models import User, UserBase


def _create_user(args: argparse.Namespace) -> User:
    conn = app.utils.sql.get_connection(args.db)
    user = models.UserBase(label=args.label, description=args.description)
    user = models.create_user(conn, user)
    print(user.id)


parser = subparsers.add_parser("users")

subparsers = parser.add_subparsers()

serve_parser = subparsers.add_parser("create")

serve_parser.add_argument("label")
serve_parser.add_argument("description", default="", nargs="?")
serve_parser.set_defaults(command=_create_user)
