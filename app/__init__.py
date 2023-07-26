import logging

logging.getLogger().setLevel(logging.DEBUG)

from . import corecli
from . import db
from . import events
from . import serve
from . import users
from . import utils

modules = [corecli, db, events, serve, users, utils]
