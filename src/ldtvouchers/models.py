from typing import NewType

from pydantic import BaseModel, Field  # type: ignore

EmissionId = NewType("EmissionId", int)
UserId = NewType("UserId", int)
VoucherId = NewType("VoucherId", int)


class UserBase(BaseModel):  # type: ignore
    label: str = Field(default="", description="A short name")
    can_cashin: bool = Field(
        default=False, description="Tells if the user can cash a voucher in"
    )
    can_cashin_by_voucherid: bool = Field(
        default=False, description="Tells if the user can use a voucher "
    )


class User(UserBase):
    userid: UserId
