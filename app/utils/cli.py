from app.corecli.cli import subparsers

from . import makeid


def _id(args):
    print(makeid(args.prefix))


parser = subparsers.add_parser("utils")

subparsers = parser.add_subparsers()

id_parser = subparsers.add_parser("id")

id_parser.add_argument("prefix")
id_parser.set_defaults(command=_id)
