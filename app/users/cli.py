from app.corecli.cli import subparsers

from app.corecli.utils import add_crud

from . import models

subparsers = subparsers.add_parser("users").add_subparsers()

add_crud(subparsers, models.UserBase, models.User, models)
