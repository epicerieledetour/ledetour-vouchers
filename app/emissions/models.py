# # emission

# emissionid, label, description, expiration_utc

# # emission_vouchers

# emissionid (unique), voucherid (unique), index

# # vouchers

# voucherid, value, status

# # vouchers_status

# distributed | cashed_in | cashed_in_undone

# # voucher view for print

# emission: expiration_utc, voucher: token, value, distributed_by

# # is cashable ?

# status != cashed_in and last_status_update_by == me and last_status_update_utc < 5min


# # token

# itemid, token (for vouchers: voucher_XXXXX, 0001_DHCFG, 0001 being the index in emission)

# TODO: move all deleted attribute in a `deleted` table,
#       so not all entities need a deleted column ?
#       Or maybe add event statuses status_delete / status_restore so there is deleted column at all ?

import csv
import sqlite3
import sys

from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel, Field

import app.utils.sql
import app.users.models as users_models
import app.vouchers.models as vouchers_models

from app.utils.models import build_crud

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])


class EmissionBase(BaseModel):
    label: str | None = Field(default=None, description="A short name")
    description: str | None = Field(
        default=None,
        description="A longer, explicit description",
    )
    expiration_utc: datetime | None = Field(
        default=None, description="The emission expiration date in UTC time"
    )


class Emission(EmissionBase):
    id: str
    deleted: bool | None = (
        None  # TODO: something is wrong, the sql queries expect a string
    )


class _Content(BaseModel):
    emissionid: str
    voucherid: str
    sortnumber: int


# TODO: rename bundle -> eventbundle
# TODO: bundle timestamd should be precise to microsecond to allow sorting
#       Use TIMESTAMP / DEFAULT TIMESTAMP
#       See https://stackoverflow.com/questions/14461851/how-to-have-an-automatic-timestamp-in-sqlite

create, read, update, delete, history = build_crud(
    EmissionBase, Emission, "emission", _SQLS
)


def export_csv(conn: sqlite3.Connection, ids: Iterable[str], fd) -> None:
    writer = csv.DictWriter(
        fd,
        # TODO: extract magic strings
        fieldnames=["voucher_index", "voucher_value_CAD", "distributor_label"],
    )
    writer.writeheader()


# TODO: make str an actual ID type (cf typing.NewType)
# TODO: add specimen vouchers at 0 USD
def import_csv(conn: sqlite3.Connection, emissionid: str, fd) -> None:
    reader = csv.DictReader(fd)

    with conn:
        # contents: emissionid, voucherid, sortnumber
        cur_contents_by_sortnumber = dict(
            (content.sortnumber, content) for content in _read_content(conn, emissionid)
        )
        cur_users_by_label = dict(
            (user.label, user) for user in users_models.read(conn)
        )
        import 

        # TODO: Make a single bundle for all these events

        for csvrow in reader:
            if csvrow["voucher_sortnumber"] in cur_contents_by_sortnumber:
                content = cur_sortnumbers.pop(csvrow["voucher_sortnumber"])

                vouchers_models.update(
                    conn,
                    [
                        vouchers_models.Voucher(
                            id=content.voucherid,
                            value_CAD=int(csvrow["voucher_value_CAD"]),
                        )
                    ],
                )
                vouchers_models.update(
                    conn,
                    [
                        vouchers_models.Voucher(
                            id=content.voucherid,
                            status=vouchers_models.STATUS_DISTRIBUTED,
                        )
                    ],
                    userid=cur_users_by_label[csvrow["distributor_label"]].id,
                )

                #### Next TODO
                # Extend query to get the last user who set the status to `distributed`
                # SELECT *, sortnumber as voucher_sortnumber, value_CAD as voucher_value_CAD
                # FROM emission_contents
                # JOIN vouchers ON emission_contents.voucherid = vouchers.id
                # WHERE emissionid = 'emission_AKMPKvpPjjy5yb3e7P4h8P'
                ####

                # TODO: Find distributor and emit event in their name to distribute voucher

            else:
                # create new voucher
                # register new voucher at index
                new_voucher = vouchers_models.create(
                    conn,
                    [
                        vouchers_models.VoucherBase(
                            value_CAD=int(csvrow["voucher_value_CAD"]),
                        )
                    ],
                )[0]
                vouchers_models.update(
                    conn,
                    [
                        vouchers_models.Voucher(
                            id=new_voucher.id,
                            status=vouchers_models.STATUS_DISTRIBUTED,
                        )
                    ],
                    userid=cur_users_by_label[csvrow["distributor_label"]].id,
                )
                _add_content(
                    conn,
                    [
                        _Content(
                            emissionid=emissionid,
                            sortnumber=csvrow["voucher_sortnumber"],
                            voucherid=new_voucher.id,
                        )
                    ],
                )

        # remove remaining cur_sortnumbers and delete vouchers


def _add_content(conn: sqlite3.Connection, contents: Iterable[_Content]) -> None:
    conn.executemany(_SQLS.contents_add, (content.dict() for content in contents))


def _read_content(conn: sqlite3.Connection, emissionid: str) -> Iterable[_Content]:
    curs = conn.execute(_SQLS.contents_read, {"emissionid": emissionid})
    return [_Content(**kwargs) for kwargs in curs.fetchall()]


# import
# 1, 10, LDT
# 2, 30, NAN
# 4, 40, LDT

# emission_contents (
#     emissionid TEXT NOT NULL,
#     voucherid TEXT NOT NULL,
#     voucher_index INT
# );
