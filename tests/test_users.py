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

    def tearDown(self):
        self.conn.close()

    # Create

    def test_create_users(self):
        self.assertEqual(len(self.users), 4)

        for base, user in zip(self.bases, self.users):
            # Test if user has all keys of base
            # Replaces assertDictContainsSubset
            # See https://stackoverflow.com/questions/20050913/python-unittests-assertdictcontainssubset-recommended-alternative
            self.assertEqual(user.dict(), user.dict() | base.dict())

            self.assertTrue(user.id)

        expected_events = [
            (events_models.CreateEvent(user.id), events_models.StatusOK())
            for user in self.users
        ]

    # Read

    def test_read_users__one(self):
        user_id = self.users[1].id
        users = tuple(users_models.read_users(self.conn, [user_id]))

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].id, user_id)

    def test_read_users__several(self):
        user_ids = (self.users[1].id, self.users[3].id)
        users = tuple(users_models.read_users(self.conn, user_ids))

        self.assertEqual(len(users), 2)
        self.assertTupleEqual(tuple(user.id for user in users), user_ids)

    def test_read_users__all_from_none(self):
        users = tuple(users_models.read_users(self.conn, None))

        expected_user_ids = tuple(user.id for user in self.users)

        self.assertEqual(len(users), 4)
        self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    def test_read_users__all_from_empty_generator(self):
        users = tuple(users_models.read_users(self.conn, range(0)))

        expected_user_ids = tuple(user.id for user in self.users)

        self.assertEqual(len(users), 4)
        self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    def test_read_users__raise_if_unknown_id(self):
        with self.assertRaises(ValueError):
            users_models.read_users(self.conn, [self.users[0].id, "unknown_id"])

    # Update

    def test_update_users(self):
        users = (
            self.users[1].copy(update={"label": "new_user1"}),
            self.users[3].copy(update={"description": "new user3 description"}),
        )

        users_models.update_users(self.conn, users)

        expected_updated_users = tuple(
            users_models.read_users(self.conn, (user.id for user in users))
        )

        self.assertTupleEqual(expected_updated_users, users)

    def test_update_users__invalid_user_fails(self):
        invalid_user = users_models.User(id="unknown", label="No label")

        with self.assertRaises(ValueError):
            users_models.update_users(self.conn, [invalid_user])

    # Delete

    def test_delete_users(self):
        users = (self.users[1], self.users[3])

        users_models.delete_users(self.conn, users)

        ids = tuple(user.id for user in users_models.read_users(self.conn, None))

        expected_ids = (self.users[0].id, self.users[2].id)

        self.assertTupleEqual(ids, expected_ids)

    def test_delete_users__invalid_user_fails(self):
        invalid_user = users_models.User(id="unknown", label="No label")

        with self.assertRaises(ValueError):
            users_models.delete_users(self.conn, [invalid_user])
