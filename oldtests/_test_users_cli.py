import json
import subprocess

from app.events import models as events_models
from app.users import models as users_models

from .utils import _ret_lines, TestCase


class UsersCliTestCase(TestCase):
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

    def test_read__unknown_id(self):
        with self.assertRaises(subprocess.CalledProcessError):
            _ret_lines(self.run_cli("users", "read", "unknown_id"))

    # List

    def test_list(self):
        ids = []

        for _ in range(3):
            ids.extend(_ret_lines(self.run_cli("users", "create")))

        lines = self.run_cli("users", "list").stdout.decode()

        # TODO: preserve creation order when listing users

        for id in ids:
            self.assertTrue(id in lines)

    # Update

    def test_update(self):
        label = "theLabel"
        description = "The description"

        ids = _ret_lines(self.run_cli("users", "create", "--label", label))
        id = ids[0]

        self.run_cli("users", "update", id, "--description", description)

        lines = self.run_cli("users", "read", id).stdout
        user = users_models.User(**json.loads(lines.decode()))

        self.assertEqual(user.label, label)
        self.assertEqual(user.description, description)

    def test_update__no_args_silently_succeeds(self):
        ids = _ret_lines(self.run_cli("users", "create"))
        id = ids[0]

        self.run_cli("users", "update", id)

        lines = self.run_cli("users", "read", id).stdout
        user = users_models.User(**json.loads(lines.decode()))

        self.assertIsNone(user.label)
        self.assertIsNone(user.description)

    # Delete

    def test_delete(self):
        ids = []
        for _ in range(3):
            ids.extend(_ret_lines(self.run_cli("users", "create")))

        self.run_cli("users", "delete", ids[0], ids[2])

        lines = self.run_cli("users", "list").stdout.decode()

        self.assertNotIn(ids[0], lines)
        self.assertIn(ids[1], lines)
        self.assertNotIn(ids[2], lines)

    # History

    def test_history(self):
        ids = _ret_lines(self.run_cli("users", "create"))
        ids.extend(_ret_lines(self.run_cli("users", "create")))

        id0, id1 = ids

        self.run_cli("users", "update", "--label", "label_mistake", id1)
        self.run_cli(
            "users", "update", "--label", "user0", "--description", "desc0", id0
        )
        self.run_cli(
            "users", "update", "--label", "user1", "--description", "desc1", id1
        )

        lines = _ret_lines(self.run_cli("users", "history", id1))

        expected = (
            (events_models._EVENT_CREATE, None, None),
            (events_models._EVENT_UPDATE, "label", None),
            (events_models._EVENT_UPDATE, "description", None),
            (events_models._EVENT_UPDATE, "deleted", "0"),
            (events_models._EVENT_UPDATE, "label", "label_mistake"),
            (events_models._EVENT_UPDATE, "label", "user1"),
            (events_models._EVENT_UPDATE, "description", "desc1"),
        )
        for line, (commandid, field, value) in zip(lines, expected):
            data = json.loads(line)
            self.assertEqual(data["commandid"], commandid)
            self.assertEqual(data["field"], field)
            self.assertEqual(data["value"], value)
