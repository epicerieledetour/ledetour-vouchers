import uvicorn

from app.corecli import parser


def serve(args):
    uvicorn.run(
        "app.main:app", host=args.host, port=args.port, log_level="debug", reload=True
    )


subs = parser.add_subparsers(title="server")

sub = subs.add_parser("serve")
sub.add_argument("--host", default="0.0.0.0")
sub.add_argument("--port", default=8000)
sub.set_defaults(command=serve)
