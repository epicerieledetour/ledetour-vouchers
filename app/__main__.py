from . import corecli
from . import serve

args = corecli.parser.parse_args()
print(dir(args))
if hasattr(args, "command"):
    print("DDDD")
    args.command(args)
