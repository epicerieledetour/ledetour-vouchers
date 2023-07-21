import sqlite3
import unittest

import app.db
import app.utils.sql

from app.events import models as events_models
from app.users import models as users_models


class UsersTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = app.utils.sql.get_connection(":memory:")
        app.db.init(self.conn)

        self.bases = [
            users_models.UserBase(label="user1", description="user1 description"),
            users_models.UserBase(label="user2", description="user2 description"),
            users_models.UserBase(label="user3", description="user2 description"),
            users_models.UserBase(label="user4", description="user2 description"),
        ]
        self.users = tuple(users_models.create_users(self.conn, self.bases))

    def test_create(self):
        self.assertEqual(len(self.users), 4)

        for base, user in zip(self.bases, self.users):
            # Test if user has all keys of base
            # Replaces assertDictContainsSubset
            # See https://stackoverflow.com/questions/20050913/python-unittests-assertdictcontainssubset-recommended-alternative
            self.assertEqual(user.dict(), user.dict() | base.dict())

            self.assert_(user.id)

        expected_events = [
            (events_models.CreateEvent(user.id), events_models.StatusOK())
            for user in self.users
        ]

    def tearDown(self):
        self.conn.close()
