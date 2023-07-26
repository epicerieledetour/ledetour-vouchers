import uvicorn

from app.corecli.cli import subparsers


def serve(args):
    uvicorn.run(
        "app.main:app", host=args.host, port=args.port, log_level="debug", reload=True
    )


parser = subparsers.add_parser("server")

subparsers = parser.add_subparsers()

serve_parser = subparsers.add_parser("serve")

serve_parser.add_argument("--host", default="0.0.0.0")
serve_parser.add_argument("--port", default=8000)
serve_parser.set_defaults(command=serve)
