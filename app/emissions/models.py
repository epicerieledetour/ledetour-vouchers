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

import sys

from datetime import datetime

from pydantic import BaseModel, Field

import app.utils.sql

from app.utils.models import build_crud

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])


class EmissionBase(BaseModel):
    label: str | None = Field(default=None, description="A short name")
    description: str | None = Field(
        default=None,
        description="A longer, explicit description",
    )
    expiration_utc: datetime | None = Field(
        default=None, description="The emssion expiration date in UTC time"
    )


class Emission(EmissionBase):
    id: str
    deleted: bool | None = (
        None  # TODO: something is wrong, the sql queries expect a string
    )


create, read, update, delete, history = build_crud(
    EmissionBase, Emission, "emission", _SQLS
)
