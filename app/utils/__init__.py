import shortuuid

from app.corecli import subparsers

from .legacy import *


def makeid(prefix: str) -> str:
    return f"{prefix}_{shortuuid.uuid()}"


def _id(args):
    print(makeid(args.prefix))


parser = subparsers.add_parser("utils")

subparsers = parser.add_subparsers()

id_parser = subparsers.add_parser("id")

id_parser.add_argument("prefix")
id_parser.set_defaults(command=_id)
