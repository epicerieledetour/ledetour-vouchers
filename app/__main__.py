from . import corecli

args = corecli.parser.parse_args()

if hasattr(args, "command"):
    args.command(args)
