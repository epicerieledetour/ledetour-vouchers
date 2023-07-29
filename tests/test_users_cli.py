import datetime
import json
import os
import pathlib
import subprocess
import sqlite3
import sys
import tempfile
import unittest

import app.db
import app.utils.sql

from app.events import models as events_models
from app.users import models as users_models


def _ret_lines(process: subprocess.CompletedProcess) -> list[str]:
    lines = process.stdout.decode().split("\n")
    return lines[:-1]


class UsersCliTestCase(unittest.TestCase):
    root_path = None

    @classmethod
    def setUpClass(cls):
        cls.root_path = pathlib.Path(
            tempfile.mkdtemp(prefix=f"test-{datetime.datetime.now().isoformat()}")
        )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root_path.rmdir()
        except OSError:
            """Root folder is not deleted so we can inspect the output
            files in case of test failure"""

    def setUp(self):
        self.path = (
            self.root_path / f"{self.__class__.__name__}.{self._testMethodName}.sqlite3"
        )

        try:
            # os.remove(self.path)
            pass
        except FileNotFoundError:
            pass

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.run_cli("db", "init")

    def tearDown(self):
        if self._outcome.success:
            # self.path.unlink()
            pass

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-Xfrozen_modules=off", "-m", "app", "--db", self.path]
            + list(args),
            check=True,
            capture_output=True,
        )

    # Create

    def test_create__empty(self):
        ids = _ret_lines(
            self.run_cli(
                "users",
                "create",
            )
        )
        lines = _ret_lines(self.run_cli("users", "read", *ids))

        for id, line in zip(ids, lines):
            self.assertTrue(id in line)

    def test_create__with_args(self):
        ids = _ret_lines(
            self.run_cli(
                "users",
                "create",
                "--label",
                "user0",
                "--description",
                "The new user description",
            )
        )
        lines = _ret_lines(self.run_cli("users", "read", *ids))

        self.assertTrue("user0" in lines[0])
        self.assertTrue("The new user description" in lines[0])

    # Read

    def test_read(self):
        expected_user_fields = (
            {"label": "user0", "description": "Description of user0"},
            {"label": "user1", "description": "Description of user1"},
            {"label": "user2", "description": "Description of user2"},
        )

        ids = []
        for fields in expected_user_fields:
            ids.extend(
                _ret_lines(
                    self.run_cli(
                        "users",
                        "create",
                        "--label",
                        fields["label"],
                        "--description",
                        fields["description"],
                    )
                )
            )

        lines = _ret_lines(self.run_cli("users", "read", *ids))
        for expected_fields, line in zip(expected_user_fields, lines):
            fields = json.loads(line)
            user = users_models.User(**fields)
            for name, value in expected_fields.items():
                self.assertEqual(getattr(user, name), value)

    # List

    def test_list(self):
        ids = []

        for _ in range(3):
            ids.extend(_ret_lines(self.run_cli("users", "create")))

        lines = self.run_cli("users", "list").stdout.decode()

        # TODO: preserve creation order when listing users

        for id in ids:
            self.assertTrue(id in lines)

    # def test_read_users__one(self):
    #     user_id = self.users[1].id
    #     users = tuple(users_models.read_users(self.conn, [user_id]))

    #     self.assertEqual(len(users), 1)
    #     self.assertEqual(users[0].id, user_id)

    # def test_read_users__several(self):
    #     user_ids = (self.users[1].id, self.users[3].id)
    #     users = tuple(users_models.read_users(self.conn, user_ids))

    #     self.assertEqual(len(users), 2)
    #     self.assertTupleEqual(tuple(user.id for user in users), user_ids)

    # def test_read_users__all_from_none(self):
    #     users = tuple(users_models.read_users(self.conn, None))

    #     expected_user_ids = tuple(user.id for user in self.users)

    #     self.assertEqual(len(users), 4)
    #     self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    # def test_read_users__all_from_empty_generator(self):
    #     users = tuple(users_models.read_users(self.conn, range(0)))

    #     expected_user_ids = tuple(user.id for user in self.users)

    #     self.assertEqual(len(users), 4)
    #     self.assertTupleEqual(tuple(user.id for user in users), expected_user_ids)

    # def test_read_users__raise_if_unknown_id(self):
    #     with self.assertRaises(ValueError):
    #         users_models.read_users(self.conn, [self.users[0].id, "unknown_id"])

    # # Update

    # def test_update_users(self):
    #     users = (
    #         self.users[1].copy(update={"label": "new_user1"}),
    #         self.users[3].copy(update={"description": "new user3 description"}),
    #     )

    #     users_models.update_users(self.conn, users)

    #     expected_updated_users = tuple(
    #         users_models.read_users(self.conn, (user.id for user in users))
    #     )

    #     self.assertTupleEqual(expected_updated_users, users)

    # def test_update_users__invalid_user_fails(self):
    #     invalid_user = users_models.User(id="unknown", label="No label")

    #     with self.assertRaises(ValueError):
    #         users_models.update_users(self.conn, [invalid_user])

    # # Delete

    # def test_delete_users(self):
    #     users = (self.users[1], self.users[3])

    #     users_models.delete_users(self.conn, users)

    #     ids = tuple(user.id for user in users_models.read_users(self.conn, None))

    #     expected_ids = (self.users[0].id, self.users[2].id)

    #     self.assertTupleEqual(ids, expected_ids)

    # def test_delete_users__invalid_user_fails(self):
    #     invalid_user = users_models.User(id="unknown", label="No label")

    #     with self.assertRaises(ValueError):
    #         users_models.delete_users(self.conn, [invalid_user])
