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
            users_models.UserBase(label="user0", description="user0 description"),
            users_models.UserBase(label="user1", description="user1 description"),
            users_models.UserBase(label="user2", description="user2 description"),
            users_models.UserBase(label="user3", description="user3 description"),
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

    def test_read_one(self):
        user_id = self.users[1].id
        users = tuple(users_models.read_users(self.conn, [user_id]))

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].id, user_id)

    def test_read_several(self):
        user_ids = (self.users[1].id, self.users[3].id)
        users = tuple(users_models.read_users(self.conn, user_ids))

        self.assertEqual(len(users), 2)
        self.assertTupleEqual(tuple(user.id for user in users), user_ids)

    def test_read_all_from_none(self):
        users = tuple(users_models.read_users(self.conn, None))

        expected_user_ids = tuple(user.id for user in self.users)

        self.assertEqual(len(users), 4)
        self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    def test_read_all_from_empty_generator(self):
        users = tuple(users_models.read_users(self.conn, range(0)))

        expected_user_ids = tuple(user.id for user in self.users)

        self.assertEqual(len(users), 4)
        self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    def test_update(self):
        pass

    def test_delete(self):
        pass

    def tearDown(self):
        self.conn.close()
