import importlib

from .corecli.cli import parser

from . import modules

for module in modules:
    name = f"{module.__name__}.cli"
    try:
        importlib.import_module(name, "app")
    except ModuleNotFoundError:
        pass

args = parser.parse_args()

if hasattr(args, "command"):
    args.command(args)
