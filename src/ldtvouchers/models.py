import datetime
from typing import NewType

from pydantic import BaseModel, Field  # type: ignore

EmissionId = NewType("EmissionId", int)
UserId = NewType("UserId", int)
VoucherId = NewType("VoucherId", int)


class UserBase(BaseModel):  # type: ignore
    label: str = Field(
        default="",
        description="A short name",
    )
    can_cashin: bool = Field(
        default=False,
        description="Tells if the user can cash a voucher in",
    )
    can_cashin_by_voucherid: bool = Field(
        default=False,
        description="Tells if the user can use a voucher",
    )


class User(UserBase):
    userid: UserId


class VoucherBase(BaseModel):
    emissionid: EmissionId = Field(
        description="The ID of the Emission the voucher belongs to"
    )
    value_CAN: int = Field(
        description="Value in CAN",
    )
    sortnumber: int = Field(
        description="Order of the voucher in its emission",
    )
    cashedin_by: UserId | None = Field(
        default=None,
        description="ID of the user who cashed the voucher in",
    )
    cashedin_utc: datetime.datetime | None = Field(
        default=None,
        description="Date the voucher has been cashed in in UTC time",
    )
    undo_expiration_utc: datetime.datetime | None = Field(
        default=None,
        description="The date until a cashed in voucher can be undone in UTC time",
    )


class Voucher(VoucherBase):
    voucherid: VoucherId


class EmissionBase(BaseModel):
    label: str | None = Field(
        default=None,
        description="Short name of the emission",
    )
    expiration_utc: datetime.datetime = Field(
        description="Expiration date in UTC time",
    )
    vouchers: list[Voucher] = Field(
        default_factory=list,
        description="List of vouchers in the emission, ordered by voucher sortnumber",
    )


class Emission(EmissionBase):
    emissionid: EmissionId
