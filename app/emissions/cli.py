from app.corecli.cli import subparsers

from app.corecli.utils import add_crud

from . import models

subparsers = subparsers.add_parser("emissions").add_subparsers()

add_crud(subparsers, models.EmissionBase, models.Emission, models)
