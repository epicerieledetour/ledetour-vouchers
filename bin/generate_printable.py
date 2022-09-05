#!/usr/bin/env python

import argparse
import itertools
import json
import pathlib
import sqlite3
import string

import jinja2


def group(iterator, count, default_factory):
    group = []
    for item in iterator:
        group.append(item)
        if len(group) == count:
            yield tuple(group)
            group.clear()

    if group:
        yield tuple(group)


def pad(items, count, default_factory):
    yield from items
    for _ in range(count - len(items)):
        yield default_factory()


def last_valid(items):
    for item in reversed(items):
        if item:
            return item


def build_voucher_template_dict(prefix, row):
    if not row:
        return {
            f"{prefix}v": "",
            f"{prefix}l": "",
            f"{prefix}c": "empty.svg",
        }

    return {
        f"{prefix}v": f"{row['value']}$",
        f"{prefix}l": row["label"],
        f"{prefix}c": row["qrcode"],
    }


parser = argparse.ArgumentParser(
    description="Generate the build system to extract vouchers and authtification pages from a database."
)
parser.add_argument(
    "db",
    type=pathlib.Path,
    help="Path to the database",
)

args = parser.parse_args()

root_dir = pathlib.Path(__file__).parent.parent
templates_dir = root_dir / "templates" / "printables"

subninja_paths = []

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(templates_dir),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)

# Vouchers

vouchers_per_page = 6

voucher_pages = []

res = conn.execute("SELECT * FROM vouchers").fetchall()
for rows in group(res, vouchers_per_page, dict):
    # Create the folder from the vouchers page

    first, last = rows[0], rows[-1]
    root = pathlib.Path(
        f"tmp/vouchers/{first['label']}-{last['label']}-{first['id']}-{last['id']}"
    )
    root.mkdir(exist_ok=True, parents=True)

    # Add qrcode paths to the rows data

    rows = [dict(qrcode=f"qrcode-{row['id']}.svg", **row) for row in rows]

    # Dump the JSON

    data_dict = {}
    for prefix, row in itertools.zip_longest(
        string.ascii_lowercase[:vouchers_per_page], rows
    ):
        data_dict.update(build_voucher_template_dict(prefix, row))

    data = root / "data.json"
    with data.open("w") as fp:
        json.dump(data_dict, fp, sort_keys=True, indent=4)

    # Output PDFs

    recto = root / "recto.pdf"
    verso = root / "verso.pdf"

    # Dump the ninja.build

    build = root / "ninja.build"

    env.get_template("vouchers/build.ninja").stream(
        templatesdir=templates_dir / "vouchers",
        assets=["empty.svg", "logo-clubpop.png", "logo-detour.jpg"],
        root=root,
        data=data.name,
        recto=recto.name,
        verso=verso.name,
        vouchers=rows,
    ).dump(str(build))

    subninja_paths.append(build)
    voucher_pages.append(recto)
    voucher_pages.append(verso)

# Users

users_pages = []

res = conn.execute("SELECT * FROM users").fetchall()
for user in res:
    # Create the folder from the user page
    root = pathlib.Path(f"tmp/users/{user['id']}")
    root.mkdir(exist_ok=True, parents=True)

    # Add qrcode paths to the rows data

    user = dict(qrcode="qrcode.svg", **user)

    # Dump the JSON

    data = root / "data.json"
    with data.open("w") as fp:
        json.dump(user, fp, sort_keys=True, indent=4)

    # Output PDF

    page = root / "user.pdf"

    # Dump the ninja.build

    build = root / "ninja.build"

    env.get_template("users/build.ninja").stream(
        root=root, data=data.name, user=user, page=page.name
    ).dump(str(build))

    subninja_paths.append(build)

    users_pages.append(page)


# Main

template = env.get_template("build.ninja")
template.stream(
    db=args.db,
    render_jinja_template=root_dir / "bin" / "render_jinja_template.py",
    templates_dir=templates_dir,
    subninja_paths=subninja_paths,
    voucher_pages=voucher_pages,
    users_pages=users_pages,
).dump("build.ninja")
