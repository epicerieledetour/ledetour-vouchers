# TODO: rename module to httpapi

import contextlib
from sqlite3 import Connection

import jinja2
from fastapi import Depends, FastAPI, Response, status
from fastapi.responses import HTMLResponse

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


# @app.get("/{requestid}/{url_token}")
# def scan(
#     response: Response,
#     requestid: str,
#     url_token: str,
#     authorization: Annotated[str, Header()] = "",
#     conn: Connection = Depends(get_db),
# ):
#     m = re.match(r"Bearer (?P<token>.+)", authorization)
#     bearer_token = m.groupdict()["token"] if m else None

#     user_token, voucher_token = (
#         (bearer_token, url_token) if bearer_token else (url_token, None)
#     )

#     action = db.add_action(
#         conn,
#         models.ActionBase(
#             origin=_ACTION_ORIGIN_HTTPAPI,
#             req_usertoken=user_token,
#             req_vouchertoken=voucher_token,
#             requestid=requestid,
#         ),
#     )

#     status_code, http_response = db.build_http_response(conn, action)

#     response.status_code = status_code

#     return http_response


_ENV = jinja2.Environment(
    loader=jinja2.PackageLoader("ldtvouchers", "templates/webapp"),
    autoescape=jinja2.select_autoescape,
)


_RESPONSES = {
    None: {  # used for the start page
        "http_return_code": status.HTTP_200_OK,
    },
    "error_voucher_unauthentified": {
        "http_return_code": status.HTTP_401_UNAUTHORIZED,
    },
    # "error_voucher_user_needs_voucher_token"
    # "error_voucher_invalid"
    # "error_voucher_expired"
    # "ok_voucher_cashedin"
    # "error_voucher_cashedin_by_another_user"
    # "warning_voucher_cannot_undo_cashedin"
    # "warning_voucher_can_undo_cashedin"
    "error_user_invalid_token": {
        "http_return_code": status.HTTP_401_UNAUTHORIZED,
        "status": "Invalid user",
    },
    "ok_user_authentified": {
        "http_return_code": status.HTTP_200_OK,
        "status": "",
    },
    # "ok_voucher_info"
    # "error_voucher_cannot_undo_cashedin"
    # "error_bad_request"
    # "ok_voucher_undo"
    # "error_voucher_cannot_undo_not_cashedin"
}

_DOMAINS = {
    None: {  # used for the start page
        "prompt": "Scan an user code",
    },
    "user": {"prompt": "Scan a voucher"},
    "voucher": {"prompt": ""},
}


@app.get("/{requestid}/{url_token}")
def scan(
    response: Response,
    requestid: str,
    url_token: str,
    conn: Connection = Depends(get_db),
):
    action = db.add_action(
        conn,
        models.ActionBase(
            origin=_ACTION_ORIGIN_HTTPAPI,
            req_usertoken=url_token,
            req_vouchertoken=None,
            requestid=requestid,
        ),
    )

    return _response(db.build_http_response(conn, action))


def _response(resp: models.HttpResponse | None) -> HTMLResponse:
    responseid = None
    level = None
    domain = None
    if resp:
        responseid = resp.status.responseid
        level = resp.status.level
        domain = resp.status.domain

    template = _ENV.get_template("index.html.j2")
    content = template.render(
        level=level,
        status=_RESPONSES[responseid].get("status", ""),
        prompt=_DOMAINS[domain]["prompt"],
    )

    status_code = _RESPONSES[responseid]["http_return_code"]

    return HTMLResponse(content=content, status_code=status_code)


@app.get("/")
def index():
    return _response(None)


# http://localhost:8080/                      # start
# http://localhost:8080/scan/tokusr_invalid   # invalid user
# http://localhost:8080/scan/tokusr_ijpxzkbf  # valid user
