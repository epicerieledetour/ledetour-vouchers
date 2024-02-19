# TODO: rename module to httpapi

import contextlib
import datetime
import functools
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

import jinja2
import pytz
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


_ENV = jinja2.Environment(
    loader=jinja2.PackageLoader("ldtvouchers.webapp"),
    autoescape=jinja2.select_autoescape,
)


def _datetime_format(date: datetime.datetime | None, format: str) -> str:
    if not date:
        return ""
    utc = pytz.utc.localize(date)
    est = utc.astimezone(pytz.timezone("Canada/Eastern"))
    return est.strftime(format)


_ENV.filters["boolstr"] = lambda v: "TRUE" if v else "FALSE"
_ENV.filters["date"] = functools.partial(_datetime_format, format="%Y-%m-%d")
_ENV.filters["datetime"] = functools.partial(
    _datetime_format, format="%Y-%m-%d %H:%M:%S"
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
    return request.url_for("user", requestid="scan", usertoken="{scanResult}")


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
    return request.url_for(
        "user",
        requestid="scan",
        usertoken=response.user.token,
    )


@_url
def _url_for_logout(request: Request, response: HTMLResponse) -> str:
    if response and response.user:
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
    logout_url_builder: Callable[[Request, HTMLResponse], str] = Field(
        default=_url_for_logout,
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
        timeout_url_builder=_url_for_scanning_user,
    ),
    # "error_voucher_user_needs_voucher_token"
    "error_voucher_invalid": ResponseData(
        http_return_code=status.HTTP_400_BAD_REQUEST,
        status="Invalid voucher",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "error_voucher_expired": ResponseData(
        http_return_code=status.HTTP_403_FORBIDDEN,
        status="Voucher has expired",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "ok_voucher_cashedin": ResponseData(
        http_return_code=status.HTTP_200_OK,
        status="Cashed in",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "error_voucher_cashedin_by_another_user": ResponseData(
        http_return_code=status.HTTP_403_FORBIDDEN,
        status="Voucher already cashed in",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "warning_voucher_cannot_undo_cashedin": ResponseData(
        http_return_code=status.HTTP_200_OK,
        status="Already cashed, too late to undo",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "warning_voucher_can_undo_cashedin": ResponseData(
        http_return_code=status.HTTP_200_OK,
        status="Voucher already cashed by you, can still undo",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
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
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "error_voucher_cannot_undo_cashedin": ResponseData(
        http_return_code=status.HTTP_403_FORBIDDEN,
        status="Cannot undo cashed in anymore",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "error_bad_request": ResponseData(
        http_return_code=status.HTTP_400_BAD_REQUEST,
        status="Invalid action",
        timeout_url_builder=_url_for_scanning_user,
    ),
    "ok_voucher_undo": ResponseData(
        http_return_code=status.HTTP_200_OK,
        status="Cashedin undone",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
    "error_voucher_cannot_undo_not_cashedin": ResponseData(
        http_return_code=status.HTTP_403_FORBIDDEN,
        status="Voucher has not been cashed in, cannot be undone",
        timeout_url_builder=_url_for_scanning_voucher,
    ),
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


@app.get("/u/{requestid}/{usertoken}/{vouchertoken}")
def voucher(
    request: Request,
    response: Response,
    requestid: str,
    usertoken: str,
    vouchertoken: str,
    conn: Connection = Depends(get_db),
):
    return _request(request, response, requestid, usertoken, vouchertoken, conn)


@app.get("/u/{requestid}/{usertoken}")
def user(
    request: Request,
    response: Response,
    requestid: str,
    usertoken: str,
    conn: Connection = Depends(get_db),
):
    vouchertoken = None
    return _request(request, response, requestid, usertoken, vouchertoken, conn)


@app.get("/d/{responseid}")
def debug(
    request: Request,
    response: Response,
    responseid: str,
    conn: Connection = Depends(get_db),
):
    action = db._read_first_action_with_responseid(conn, responseid)
    return _response(request, db.build_http_response(conn, action) if action else None)


def _request(
    request: Request,
    response: Response,
    requestid: str,
    usertoken: str,
    vouchertoken: str,
    conn: Connection,
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
        responseid=responseid,
        title=_TITLE,
        level=level,
        user=user,
        voucher=voucher,
        logout_url=data.logout_url_builder(request, resp),
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
# http://localhost:8080/u/scan/tokusr_hpo4wu5v/0001-XUQNS

app.mount("/", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
