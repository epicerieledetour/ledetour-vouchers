# TODO: rename module to httpapi

import contextlib
import re
from sqlite3 import Connection
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Response

from . import db, models

app = FastAPI()

_ACTION_ORIGIN_HTTPAPI = "httpapi"

# Dependencies


class DBGetter:
    def __init__(self):
        self.dbpath = None

    def __call__(self):
        conn = db.connect(self.dbpath)

        with contextlib.closing(conn):
            with conn:
                yield conn


get_db = DBGetter()


@app.get("/scan/{url_token}")
def scan(
    response: Response,
    url_token,
    authorization: Annotated[str, Header()] = "",
    conn: Connection = Depends(get_db),
):
    m = re.match(r"Bearer (?P<token>.+)", authorization)
    bearer_token = m.groupdict()["token"] if m else None

    user_token, voucher_token = (
        (bearer_token, url_token) if bearer_token else (url_token, None)
    )

    action = db.add_action(
        conn,
        models.ActionBase(
            origin=_ACTION_ORIGIN_HTTPAPI,
            req_usertoken=user_token,
            req_vouchertoken=voucher_token,
            requestid="scan",
        ),
    )

    status_code, http_response = db.build_http_response(conn, action)

    response.status_code = status_code

    return http_response
