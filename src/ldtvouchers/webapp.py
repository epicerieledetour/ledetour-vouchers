# TODO: rename module to httpapi

import contextlib
import datetime
from sqlite3 import Connection

import jinja2
from fastapi import Depends, FastAPI, Request, Response, status
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
    "error_voucher_invalid": {
        "http_return_code": status.HTTP_400_BAD_REQUEST,
        "status": "Invalid voucher",
    },
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


def _url_for_user(request: Request, response: HTMLResponse) -> str:
    return request.url_for("user", usertoken=response.user.token)


def _noop(*_, **__) -> None:
    return None


_DOMAINS = {
    None: {  # used for the start page
        "prompt": "Scan an user code",
        "scan": True,
        "timeout": None,
        "timeout_nexturl_builder": _noop,
    },
    "user": {
        "prompt": "Scan a voucher",
        "scan": True,
        "timeout": None,
        "timeout_nexturl_builder": _noop,
    },
    "voucher": {
        "prompt": "",
        "scan": False,
        "timeout": datetime.timedelta(seconds=10),
        "timeout_nexturl_builder": _url_for_user,
    },
}


@app.get("/{requestid}/{usertoken}/{vouchertoken}")
def voucher(
    request: Request,
    response: Response,
    requestid: str,
    usertoken: str,
    vouchertoken: str,
    conn: Connection = Depends(get_db),
):
    action = db.add_action(
        conn,
        models.ActionBase(
            origin=_ACTION_ORIGIN_HTTPAPI,
            req_usertoken=usertoken,
            req_vouchertoken=vouchertoken,
            requestid=requestid,
        ),
    )

    return _response(request, db.build_http_response(conn, action))


@app.get("/scan/{usertoken}")
def user(
    request: Request,
    response: Response,
    usertoken: str,
    conn: Connection = Depends(get_db),
):
    action = db.add_action(
        conn,
        models.ActionBase(
            origin=_ACTION_ORIGIN_HTTPAPI,
            req_usertoken=usertoken,
            req_vouchertoken=None,
            requestid="scan",
        ),
    )

    return _response(request, db.build_http_response(conn, action))


def _response(request: Request, resp: models.HttpResponse | None) -> HTMLResponse:
    responseid = None
    level = None
    domain = None
    if resp:
        responseid = resp.status.responseid
        level = resp.status.level
        domain = resp.status.domain

    template = _ENV.get_template("index.html.j2")
    import pprint

    pprint.pprint(resp)
    pprint.pprint(_DOMAINS[domain])

    content = template.render(
        level=level,
        status=_RESPONSES[responseid].get("status", ""),
        prompt=_DOMAINS[domain]["prompt"],
        scan=_DOMAINS[domain]["scan"],
        timeout=_DOMAINS[domain]["timeout"],
        timeout_nexturl=_DOMAINS[domain]["timeout_nexturl_builder"](request, resp),
    )

    status_code = _RESPONSES[responseid]["http_return_code"]

    return HTMLResponse(content=content, status_code=status_code)


@app.get("/")
def index(request: Request):
    return _response(request, None)


# http://localhost:8080/                      # start
# http://localhost:8080/scan/tokusr_invalid   # invalid user
# http://localhost:8080/scan/tokusr_ijpxzkbf  # valid user
