import sys

from pydantic import BaseModel, Field

import app.utils.sql

from app.utils.models import build_crud

_SQLS = app.utils.sql.get_module_queries(sys.modules[__name__])

# TODO: make it an enum
STATUS_DISTRIBUTED = "distributed"
STATUS_CASHEDIN = "cashedin"
STATUS_CASHEDIN_UNDONE = "cashedin_undone"


class VoucherBase(BaseModel):
    label: str | None = Field(default=None, description="A short user name, ie. LDT")
    description: str | None = Field(
        default=None,
        description="A longer, explicit user description, ie. 'Le Détour Cashier #1'",
    )
    value_CAD: int | None = Field(
        default=None, description="The value of the voucher in Canadian dollars"
    )
    # TODO: make it an enum
    # TODO: document the potential values in the description
    status: str | None = Field(default=None, description="The status of the voucher")


class Voucher(VoucherBase):
    # TODO: use pattern validator voucher_*
    id: str
    deleted: bool | None = None


create, read, update, delete, history = build_crud(
    VoucherBase, Voucher, "voucher", _SQLS
)
