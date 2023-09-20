import datetime
import functools
import itertools
import pathlib
import string
import tempfile
from io import StringIO
from sqlite3 import Connection
from typing import Any, BinaryIO, Callable

import cairosvg
import jinja2
import odf.opendocument
import qrcode
import qrcode.image.svg
from pypdf import PdfWriter

from . import db, models

_ENV = jinja2.Environment(
    loader=jinja2.PackageLoader("ldtvouchers"), autoescape=jinja2.select_autoescape
)

_TEMPLATES_PATH = pathlib.Path(__file__).parent / "templates/vouchers"

_EMPTY_QRCODE_PATH = _TEMPLATES_PATH / "empty.svg"
_VOUCHERS_VERSO_SVG_PATH = _TEMPLATES_PATH / "verso.svg"

_EMPTY_VOUCHER = models.PublicVoucher(
    emissionid=-1,
    sortnumber=-1,
    token="",
    value_CAN=0,
)
_VOUCHERS_PER_PAGE_COUNT = 6

_svg2pdf = functools.partial(cairosvg.svg2pdf, unsafe=True)


def _tmpdir(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        with tempfile.TemporaryDirectory(
            prefix=f"ldtvouchers-gen-{func.__name__}-", ignore_cleanup_errors=True
        ) as path:
            return func(*args, tmpdir=pathlib.Path(path), **kwargs)

    return wrap


@_tmpdir
def user_authpage(user: models.PublicUser, fp: BinaryIO, tmpdir: pathlib.Path) -> None:
    template = _ENV.get_template("user_authpage.svg.j2")

    svg = template.render(
        user=user,
        qrcode_svg_path=_write_qrcode(user.token, tmpdir / "qrcode.svg"),
        document_date=datetime.datetime.now().replace(microsecond=0),
    )
    _svg2pdf(bytestring=svg, write_to=fp)


def _write_qrcode(value: str, path: pathlib.Path) -> pathlib.Path:
    if not value:
        return _EMPTY_QRCODE_PATH

    img = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage)
    with path.open("wb") as fp:
        img.save(fp)

    return path


@_tmpdir
def emission_vouchers(
    emission: models.PublicEmission, fp: BinaryIO, tmpdir: pathlib.Path
) -> None:
    def _groupby(count: int) -> Callable[[Any], bool]:
        cur = -1

        def key(_):
            nonlocal cur
            cur += 1
            return cur // count

        return key

    def _pages():
        for i, vouchers in itertools.groupby(
            emission.vouchers, _groupby(_VOUCHERS_PER_PAGE_COUNT)
        ):
            vouchers = list(vouchers)
            pad_count = _VOUCHERS_PER_PAGE_COUNT - len(vouchers)
            vouchers = vouchers + pad_count * [_EMPTY_VOUCHER]

            yield i, vouchers

    def _args(vouchers):
        prefixes = iter(string.ascii_lowercase)

        ret = {}
        for v in vouchers:
            p = next(prefixes)
            ret.update(
                {
                    f"{p}c": _write_qrcode(v.token, tmpdir / f"{v.token}.svg"),
                    f"{p}d": expiration_date_str,
                    f"{p}i": v.token,
                    f"{p}v": v.value_CAN,
                }
            )
        return ret

    expiration_date_str = (
        emission.expiration_utc.date().isoformat() if emission.expiration_utc else ""
    )

    # Initialize the PDF merger

    pdf_merger = PdfWriter()

    # Convert the verso SVG to a temporary PDF

    verso_pdf_path = tmpdir / "verso.pdf"
    with verso_pdf_path.open("wb") as fd:
        _svg2pdf(url=str(_VOUCHERS_VERSO_SVG_PATH), write_to=fd)

    # Initialize the jinja environment

    template = _ENV.get_template("vouchers/recto.svg.j2")

    # Write each PDF page

    for page_number, vouchers in _pages():
        svg = template.render(**_args(vouchers))

        pdf = tmpdir / "recto_{page_number:04d}.pdf"

        with pdf.open("wb") as fd:
            _svg2pdf(bytestring=svg, write_to=fd)

        pdf_merger.append(fileobj=pdf)
        pdf_merger.append(fileobj=verso_pdf_path)

    # Merge all pages and output the final PDF

    pdf_merger.write(fp)


def emission_htmlreport(
    conn: Connection,
    emissionid: models.EmissionId,
    fp: BinaryIO,
) -> None:
    template = _ENV.get_template("emission_htmlreport.html.j2")

    args = {"emissionid": emissionid}
    template.stream(
        emission=conn.execute(
            db.get_sql("emission_htmlreport_emission"), args
        ).fetchone(),
        vouchers=conn.execute(
            db.get_sql("emission_htmlreport_vouchers"), args
        ).fetchall(),
        actions=conn.execute(
            db.get_sql("emission_htmlreport_actions"), args
        ).fetchall(),
    ).dump(fp)


def emission_odsreport(conn: Connection, fp: StringIO) -> None:
    doc = odf.opendocument.OpenDocumentSpreadsheet()
    doc.write(fp)
