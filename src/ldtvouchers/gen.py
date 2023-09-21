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
import odf.number
import odf.opendocument
import odf.style
import odf.table
import odf.text
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


_ODF_VALUETYPE_MAPPING = (
    (
        str,
        lambda val: (
            {
                "valuetype": "string",
            },
            val,
        ),
    ),
    (
        bool,
        lambda val: (
            {
                "valuetype": "boolean",
                "booleanvalue": str(val).lower(),
            },
            val,
        ),
    ),
    (
        float,
        lambda val: (
            {
                "valuetype": "float",
                "value": val,
            },
            val,
        ),
    ),
    (
        int,
        lambda val: (
            {
                "valuetype": "float",
                "value": val,
            },
            val,
        ),
    ),
    (
        datetime.datetime,
        lambda val: (
            {
                "valuetype": "date",
                "datevalue": val.isoformat(),
            },
            val.isoformat(),
        ),
    ),
)


def _transform(val):
    if not isinstance(val, datetime.datetime):
        try:
            return datetime.datetime.fromisoformat(val)
        except (TypeError, ValueError):
            pass
    return val


def _table_cell_args(val):
    val = _transform(val)
    for typ, func in _ODF_VALUETYPE_MAPPING:
        if isinstance(val, typ):
            return func(val)
    func = _ODF_VALUETYPE_MAPPING[0][1]
    return func(val)


def emission_odsreport(conn: Connection, fp: StringIO) -> None:
    def _table_column_args(val):
        val = _transform(val)
        ret = {}
        if isinstance(val, bool):
            ret["defaultcellstylename"] = "auto-bool-style"  # pragma: no cover
        if isinstance(val, datetime.datetime):
            ret["defaultcellstylename"] = "auto-date-style"  # pragma: no cover
        return ret

    def _add_table(name, rows):
        table = odf.table.Table(parent=doc.spreadsheet, name=name)

        first_row = True

        for row in rows:
            if first_row:
                first_row = False
                hcol = odf.table.TableHeaderColumns(parent=table)

                for val in tuple(row):
                    odf.table.TableColumn(parent=hcol, **_table_column_args(val))

                tr = odf.table.TableRow(parent=table)
                for val in row.keys():
                    _add_row_cell(tr, val)

            tr = odf.table.TableRow(parent=table)
            for val in tuple(row):
                _add_row_cell(tr, val)

    def _add_row_cell(tr, val, **kwargs):
        args, text = _table_cell_args(val)
        kwargs.update(args)
        cl = odf.table.TableCell(parent=tr, **kwargs)
        cl.addElement(odf.text.P(text=text))

    def _add_info_table():
        table = odf.table.Table(parent=doc.spreadsheet, name="info")
        tr = odf.table.TableRow(parent=table)
        _add_row_cell(tr, "generation_date")
        _add_row_cell(tr, datetime.datetime.now(), stylename="auto-date-style")

    doc = odf.opendocument.OpenDocumentSpreadsheet()

    # Date style

    date_style = odf.number.DateStyle(parent=doc.automaticstyles, name="date-style")
    odf.number.Year(parent=date_style, style="long")
    odf.number.Text(parent=date_style, text="-")
    odf.number.Month(parent=date_style, style="long")
    odf.number.Text(parent=date_style, text="-")
    odf.number.Day(parent=date_style, style="long")

    odf.number.Text(parent=date_style, text=" ")

    odf.number.DayOfWeek(parent=date_style, style="long")

    odf.number.Text(parent=date_style, text=" ")

    odf.number.Hours(parent=date_style, style="long")
    odf.number.Text(parent=date_style, text=":")
    odf.number.Minutes(parent=date_style, style="long")
    odf.number.Text(parent=date_style, text=":")
    odf.number.Seconds(parent=date_style, style="long")

    odf.style.Style(
        parent=doc.automaticstyles,
        name="auto-date-style",
        family="table-cell",
        parentstylename="Default",
        datastylename="date-style",
    )

    # Boolean style

    bool_style = odf.number.BooleanStyle(parent=doc.automaticstyles, name="bool-style")
    odf.number.Boolean(parent=bool_style)

    odf.style.Style(
        parent=doc.automaticstyles,
        name="auto-bool-style",
        family="table-cell",
        parentstylename="Default",
        datastylename="bool-style",
    )

    # Tables

    _add_table(
        "vouchers", conn.execute(db.get_sql("emission_odsreport_vouchers")).fetchall()
    )
    _add_table(
        "actions", conn.execute(db.get_sql("emission_odsreport_actions")).fetchall()
    )
    _add_info_table()

    # Write

    doc.write(fp)
