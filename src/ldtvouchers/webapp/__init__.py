# TODO: rename module to httpapi

import contextlib
import datetime
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

import jinja2
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field  # type: ignore

from .. import db, models

app = FastAPI()

_ACTION_ORIGIN_HTTPAPI = "httpapi"

_TITLE = "Bons solidaires"

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
    loader=jinja2.PackageLoader("ldtvouchers.webapp"),
    autoescape=jinja2.select_autoescape,
)


def _noop(*_, **__) -> None:
    return None


def _url(func):
    def wrap(*args, **kwargs):
        ret = func(*args, **kwargs)
        return str(ret)

    return wrap


def _js_template(func):
    def wrap(*args, **kwargs):
        ret = func(*args, **kwargs)
        return f"`{ret}`"

    return wrap


@_js_template
@_url
def _url_template_for_scanning_user(request: Request, response: HTMLResponse) -> str:
    return request.url_for("user", usertoken="{scanResult}")


@_js_template
@_url
def _url_template_for_scanning_voucher(request: Request, response: HTMLResponse) -> str:
    return request.url_for(
        "voucher",
        requestid="scan",
        usertoken=response.user.token,
        vouchertoken="{scanResult}",
    )


@_url
def _url_for_scanning_user(request: Request, response: HTMLResponse) -> str:
    return request.url_for("index")


@_url
def _url_for_scanning_voucher(request: Request, response: HTMLResponse) -> str:
    return request.url_for("user", usertoken=response.user.token)


@_url
def _url_for_exit(request: Request, response: HTMLResponse) -> str:
    if not response:
        return ""

    if response.status.level != "ok":
        return ""

    if response.voucher:
        return _url_for_scanning_voucher(request, response)

    if response.user:
        return _url_for_scanning_user(request, response)

    return ""


class Timeout(BaseModel):
    url: str
    milliseconds: int


class ResponseData(BaseModel):
    http_return_code: int = Field(
        description="The HTTP code returned when reaching this page",
    )
    prompt: str = Field(
        default="",
        description="The promp message, usually a request to scan an user code or voucher",
    )
    status: str = Field(
        default="",
        description="The status message, usually a success / warning / error string",
    )
    exit_url_builder: Callable[[Request, HTMLResponse], str] = Field(
        default=_url_for_exit,
        description="The status message, usually a success / warning / error string",
    )
    scan_url_builder: Callable[[Request, HTMLResponse], str] = Field(
        default=_noop,
        description="A callable to build the JS function that make the URL to follow after a scan",
    )
    timeout_milliseconds: int = Field(
        default=5000,
        description="Timeout time",
    )
    timeout_url_builder: Callable[[Request, HTMLResponse], str] | None = Field(
        default=None,
        description="A callable to build the URL to follow after the timeout",
    )


_RESPONSES = {
    # used for the start page
    None: ResponseData(
        http_return_code=status.HTTP_200_OK,
        prompt="Scan an user code",
        scan_url_builder=_url_template_for_scanning_user,
    ),
    "error_voucher_unauthentified": ResponseData(
        http_return_code=status.HTTP_401_UNAUTHORIZED,
        status="Invalid user",
        timeout=datetime.timedelta(seconds=5),
        timeout_url_builder=_url_for_scanning_user,
    ),
    # "error_voucher_user_needs_voucher_token"
    "error_voucher_invalid": ResponseData(
        http_return_code=status.HTTP_400_BAD_REQUEST,
        status="Invalid voucher",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    # "error_voucher_expired"
    # "ok_voucher_cashedin"
    # "error_voucher_cashedin_by_another_user"
    # "warning_voucher_cannot_undo_cashedin"
    # "warning_voucher_can_undo_cashedin"
    "error_user_invalid_token": ResponseData(
        http_return_code=status.HTTP_401_UNAUTHORIZED,
        status="Invalid user",
        timeout_url_builder=_url_for_scanning_user,
    ),
    "ok_user_authentified": ResponseData(
        http_return_code=status.HTTP_200_OK,
        prompt="Scan a voucher",
        scan_url_builder=_url_template_for_scanning_voucher,
    ),
    "ok_voucher_info": ResponseData(
        http_return_code=status.HTTP_200_OK,
        # timeout_url_builder=_url_for_scanning_voucher,
    ),
    # "error_voucher_cannot_undo_cashedin"
    # "error_bad_request"
    # "ok_voucher_undo"
    # "error_voucher_cannot_undo_not_cashedin"
}


def _url_for_user(request: Request, response: HTMLResponse) -> str:
    return request.url_for("user", usertoken=response.user.token)


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
    level = "info"
    user = None
    voucher = None
    if resp:
        responseid = resp.status.responseid
        level = resp.status.level
        user = resp.user
        voucher = resp.voucher

    data = _RESPONSES[responseid]

    timeout = None
    if data.timeout_milliseconds and data.timeout_url_builder:
        timeout = Timeout(
            url=data.timeout_url_builder(request, resp),
            milliseconds=data.timeout_milliseconds,
        )

    template = _ENV.get_template("index.html.j2")

    content = template.render(
        title=_TITLE,
        level=level,
        user=user,
        voucher=voucher,
        exit_url=data.exit_url_builder(request, resp),
        scan_url=data.scan_url_builder(request, resp),
        timeout=timeout,
        **data.model_dump(),
    )

    return HTMLResponse(content=content, status_code=data.http_return_code)


@app.get("/")
def index(request: Request):
    return _response(request, None)


# http://localhost:8080/                      # start
# http://localhost:8080/scan/tokusr_invalid   # invalid user
# http://localhost:8080/scan/tokusr_ijpxzkbf  # valid user

app.mount("/", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
