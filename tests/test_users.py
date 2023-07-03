import sqlite3
import unittest

import app.db
from app.users import models


class UsersTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect("/tmp/db.sqlite3")
        app.db.init(self.conn)

    def test(self):
        models.create_user(
            self.conn, models.UserBase(label="theUser", description="theDescription")
        )
        #         self.conn.execute(
        #             """
        # INSERT OR REPLACE INTO events (id, bundleid, timestamp_utc, commandid, elemid, statusid)
        # VALUES (
        #     'theID',
        #     'theBundleId',
        #     DATETIME('now'),
        #     'theCommandId',
        #     'theElemId',
        #     'theStatusId'
        # );
        # """
        #         )
        # self.conn.commit()
        with self.conn:
            res = self.conn.execute("SELECT * from events")
            self.assertEqual(len(res.fetchall()), 1)

    def tearDown(self):
        self.conn.close()
