import logging

import app

from app.utils import sql

from sqlite3 import Connection


def init(conn: Connection) -> None:
    with conn:
        for module in app.modules:
            sqls = sql.get_module_queries(module)
            if hasattr(sqls, "init"):
                logging.debug(f"Executing {module.__name__} init.sql")
                conn.executescript(sqls.init)
