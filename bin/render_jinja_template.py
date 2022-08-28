#!/usr/bin/env python3

import argparse
import json
import sys

import jinja2


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse a JSON and render it as Jinja template"
    )
    parser.add_argument(
        "--searchpath", default="templates", help="The search path of Jinja2 templates."
    )
    parser.add_argument(
        "--template", default="index.html", help="The template to instanciate"
    )

    return parser.parse_args()


def main(infp, outfp, searchpath, template):
    context = json.load(infp)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    env.get_template(template).stream(**context).dump(outfp)


if __name__ == "__main__":
    args = parse_args()
    main(sys.stdin, sys.stdout, args.searchpath, args.template)
