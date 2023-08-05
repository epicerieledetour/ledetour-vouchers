import logging

import app

from app.utils import sql

from sqlite3 import Connection, OperationalError


def init(conn: Connection) -> None:
    with conn:
        for module in app.modules:
            sqls = sql.get_module_queries(module)
            if hasattr(sqls, "init"):
                try:
                    conn.executescript(sqls.init)
                except OperationalError:
                    logging.fatal(f"SQL error in {module.__name__} init.sql")
                    raise
