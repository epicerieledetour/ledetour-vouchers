import contextlib
import datetime
import functools
import itertools
import pathlib
import string
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

_EMPTY_VOUCHER = models.PublicVoucher(
    emissionid=-1,
    sortnumber=-1,
    token="",
    value_CAN=0,
)
_VOUCHERS_PER_PAGE_COUNT = 6

_svg2pdf = functools.partial(cairosvg.svg2pdf, unsafe=True)


class _User(models.PublicUser):
    qrcode_svg_path: str


# @contextlib.contextmanager
# def _tmpdir(name: str) -> Generator[pathlib.Path, None, None]:
#     with tempfile.TemporaryDirectory(
#         prefix=f"ldtvouchers-gen-{name}-", ignore_cleanup_errors=True
#     ) as tmp:
#         yield pathlib.Path(tmp.name)


def _tmpdir(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        with tempfile.TemporaryDirectory(
            prefix=f"ldtvouchers-gen-{func.__name__}-", ignore_cleanup_errors=True
        ) as path:
            return func(*args, tmpdir=pathlib.Path(path), **kwargs)

    return wrap


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
                    f"{p}d": emission.expiration_utc.date().isoformat(),
                    f"{p}i": v.token,
                    f"{p}v": v.value_CAN,
                }
            )
        return ret

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
