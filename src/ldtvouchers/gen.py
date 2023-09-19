import contextlib
import datetime
import pathlib
import tempfile
from typing import BinaryIO

import cairosvg
import jinja2
import qrcode
import qrcode.image.svg

from . import models

_ENV = jinja2.Environment(
    loader=jinja2.PackageLoader("ldtvouchers"), autoescape=jinja2.select_autoescape
)


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
        pathlib.Path("/tmp/test.svg").write_text(tmpsvg)
        cairosvg.svg2pdf(bytestring=tmpsvg, write_to=fp, unsafe=True)


@contextlib.contextmanager
def _qrcode_path(value: str) -> pathlib.Path:
    img = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage)

    prefix = f"ldtvoucher-qrcode-{value}-"
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix=".svg") as fp:
        img.save(fp)

        yield fp.name
