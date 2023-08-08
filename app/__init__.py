import logging

from . import corecli
from . import db
from . import emissions
from . import events
from . import serve
from . import users
from . import utils
from . import vouchers

modules = [
    corecli,
    # db and events need to be registered before the other modules
    # as they define the elems view
    db,
    events,
    emissions,
    serve,
    users,
    utils,
    vouchers,
]
