import contextlib
import datetime
import itertools
import pathlib
import tempfile
from typing import Any, BinaryIO, Callable

import cairosvg
import jinja2
import qrcode
import qrcode.image.svg
from pypdf import PdfWriter

from . import models

_ENV = jinja2.Environment(
    loader=jinja2.PackageLoader("ldtvouchers"), autoescape=jinja2.select_autoescape
)

_TEMPLATES_PATH = pathlib.Path(__file__).parent / "templates/vouchers"

_EMPTY_QRCODE_PATH = _TEMPLATES_PATH / "empty.svg"
_VOUCHERS_VERSO_SVG_PATH = _TEMPLATES_PATH / "verso.svg"


class _User(models.PublicUser):
    qrcode_svg_path: str


def user_authpage(user: models.PublicUser, fp: BinaryIO) -> None:
    template = _ENV.get_template("user_authpage.svg.j2")

    document_date = datetime.datetime.now().replace(microsecond=0)

    with _qrcode_path(user.token) as qrcode_svg_path:
        user = _User(
            **user.model_dump(),
            qrcode_svg_path=str(qrcode_svg_path),
        )

        tmpsvg = template.render(
            user=user, qrcode_svg_path=qrcode_svg_path, document_date=document_date
        )
        cairosvg.svg2pdf(bytestring=tmpsvg, write_to=fp, unsafe=True)


@contextlib.contextmanager
def _qrcode_path(value: str) -> pathlib.Path:
    if not value:
        yield _EMPTY_QRCODE_PATH
        return

    img = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage)

    prefix = f"ldtvoucher-qrcode-{value}-"
    with tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=".svg") as fp:
        img.save(fp)
        fp.flush()

        yield fp.name


def emission_vouchers(emission: models.PublicEmission, fp: BinaryIO) -> None:
    verso_pdf_path = pathlib.Path("/tmp/verso.pdf")
    with verso_pdf_path.open("wb") as pdf:
        cairosvg.svg2pdf(url=str(_VOUCHERS_VERSO_SVG_PATH), write_to=pdf, unsafe=True)

    template = _ENV.get_template("vouchers/recto.svg.j2")

    pdf_merger = PdfWriter()

    for i, vouchers in itertools.groupby(emission.vouchers, _groupby(6)):
        vouchers = list(vouchers)
        vouchers = vouchers + (6 - len(vouchers)) * [
            models.PublicVoucher(
                emissionid=-1,
                sortnumber=-1,
                token="",
                value_CAN=0,
            )
        ]

        expiration_str = emission.expiration_utc.date().isoformat()
        a, b, c, d, e, f = vouchers

        with _qrcode_path(a.token) as ac, _qrcode_path(b.token) as bc, _qrcode_path(
            c.token
        ) as cc, _qrcode_path(d.token) as dc, _qrcode_path(e.token) as ec, _qrcode_path(
            f.token
        ) as fc:
            tmpsvg = template.render(
                # top left
                ac=ac,
                ad=expiration_str,
                ai=a.token,
                av=a.value_CAN,
                # top right
                bc=bc,
                bd=expiration_str,
                bi=b.token,
                bv=b.value_CAN,
                # middle left
                cc=cc,
                cd=expiration_str,
                ci=c.token,
                cv=c.value_CAN,
                # middle right
                dc=dc,
                dd=expiration_str,
                di=d.token,
                dv=d.value_CAN,
                # bottom left
                ec=ec,
                ed=expiration_str,
                ei=e.token,
                ev=e.value_CAN,
                # bottom right
                fc=fc,
                fd=expiration_str,
                fi=f.token,
                fv=f.value_CAN,
            )
            pathlib.Path(f"/tmp/recto_{i:04d}.svg").write_text(tmpsvg)

            tmppdf = pathlib.Path(f"/tmp/recto_{i:04d}.pdf")

            with tmppdf.open("wb") as tmpfp:
                cairosvg.svg2pdf(bytestring=tmpsvg, write_to=tmpfp, unsafe=True)

            pdf_merger.append(fileobj=tmppdf)
            pdf_merger.append(fileobj=verso_pdf_path)

    pdf_merger.write(fp)


def _groupby(count: int) -> Callable[[Any], bool]:
    cur = -1

    def key(_):
        nonlocal cur
        cur += 1
        return cur // count

    return key
