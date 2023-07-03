import logging

from . import corecli
from . import db
from . import events
from . import serve
from . import users
from . import utils

logging.getLogger().setLevel(logging.DEBUG)

modules = [corecli, db, events, serve, users, utils]
