import datetime
import json
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import testutils
from ldtvouchers import cli, db, models


class _Std:
    def __init__(self, outio=None, errio=None):
        self.errio = StringIO() if outio is None else outio
        self.outio = StringIO() if errio is None else errio

    @property
    def err(self):
        return self.errio.getvalue()

    @property
    def out(self):
        return self.outio.getvalue()

    @property
    def outlines(self):
        return self.out.split("\n")

    def load(self, model):
        return model(**json.loads(self.out))

    def validate(self, model):
        model.validate(json.loads(self.out))


class CliTestCase(unittest.TestCase):
    unknown_id = 42

    def setUp(self):
        super().setUp()

        self._tmpdir = tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers-", ignore_cleanup_errors=True
        )
        self.tmpdir = Path(self._tmpdir.name)
        self.dbpath = self.tmpdir / "db.sqlite3"

        with self.cli("db", "init"):
            pass

    def tearDown(self):
        self._tmpdir.cleanup()

        super().tearDown()

    @contextmanager
    def cli(self, *args, outio=None, errio=None):
        std = _Std()
        with redirect_stderr(std.errio), redirect_stdout(std.outio):
            cli.parse_args(["--db", str(self.dbpath)] + [str(arg) for arg in args])
            yield std

    @contextmanager
    def assertUnknownId(self):
        with self.assertRaises(SystemExit) as cm:
            yield

        err = cm.exception.args[0]

        self.assertTrue(isinstance(err, db.UnknownId))
        self.assertRegex(str(err), r"^Unknown \w+ .+$")


class CliDbTestCase(unittest.TestCase, testutils.TestCaseMixin):
    def test_init(self):
        with self.tmpdir() as root:
            db = root / "db.sqlite3"

            cli.parse_args(["--db", str(db), "db", "init"])

            self.assertTrue(db.exists())


class CliUsersTestCase(CliTestCase):
    def test_create__no_argument(self):
        with self.cli("users", "create") as std:
            std.validate(models.User)

    def test_create(self):
        label = "testuser"
        can_cashin = True
        with self.cli(
            "users", "create", "--label", label, "--can_cashin", can_cashin
        ) as std:
            user = std.load(models.User)
            self.assertEqual(user.label, label)
            self.assertTrue(user.can_cashin)
            self.assertFalse(user.can_cashin_by_voucherid)

    def test_read(self):
        with self.cli("users", "create") as std:
            created = std.load(models.User)

        with self.cli("users", "read", created.userid) as std:
            read = std.load(models.User)

        self.assertEqual(created, read)

    def test_read__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "read", self.unknown_id):
                pass

    def test_list(self):
        with self.cli("users", "create") as std:
            user1 = std.load(models.User)

        with self.cli("users", "create") as std:
            user2 = std.load(models.User)

        with self.cli("users", "list") as std:
            line1, line2, _ = std.outlines

            self.assertIn(str(user1.userid), line1)
            self.assertIn(str(user2.userid), line2)

    def test_update(self):
        with self.cli("users", "create") as std:
            user = std.load(models.User)
            self.assertEqual(user.label, "")

        userid = user.userid
        label = "userLabel"

        with self.cli("users", "update", userid, "--label", label) as std:
            user = std.load(models.User)
            self.assertEqual(user.userid, userid)
            self.assertEqual(user.label, label)

    def test_update__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "update", self.unknown_id, "--label", "lbl"):
                pass

    def test_delete(self):
        with self.cli("users", "create") as std:
            user = std.load(models.User)
            userid = user.userid

        with self.cli("users", "delete", userid) as std:
            self.assertFalse(std.out)

        with self.assertUnknownId():
            with self.cli("users", "read", userid) as std:
                pass

    def test_delete__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "delete", self.unknown_id):
                pass


class EmissionsTestCase(CliTestCase):
    def setUp(self):
        super().setUp()

        with self.cli("emissions", "create") as std:
            self.emission = std.load(models.Emission)

    def test_create__empty(self):
        with self.cli("emissions", "create") as std:
            emission = std.load(models.Emission)

            self.assertIsInstance(emission, models.Emission)

    def test_create(self):
        label = "emissionLabel"
        expiration_str = "2042-12-31"
        expiration_utc = datetime.datetime.fromisoformat(expiration_str)

        with self.cli(
            "emissions", "create", "--expiration_utc", expiration_str, "--label", label
        ) as std:
            emission = std.load(models.Emission)

            self.assertEqual(emission.label, label)
            self.assertEqual(emission.expiration_utc, expiration_utc)

    def test_read(self):
        with self.cli("emissions", "read", self.emission.emissionid) as std:
            emission = std.load(models.Emission)

        self.assertEqual(self.emission, emission)

    def test_read__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("emissions", "read", self.unknown_id):
                pass

    def test_list(self):
        with self.cli("emissions", "create") as std:
            emission = std.load(models.Emission)

        with self.cli("emissions", "list") as std:
            line1, line2, _ = std.outlines

            self.assertIn(str(self.emission.emissionid), line1)
            self.assertIn(str(emission.emissionid), line2)

    def test_update(self):
        label = "emissionLabel"

        with self.cli(
            "emissions", "update", self.emission.emissionid, "--label", label
        ) as std:
            emission = std.load(models.Emission)

            self.emission.label = label

            self.assertEqual(self.emission, emission)

    def test_update__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "update", self.unknown_id, "--label", "lbl"):
                pass

    def test_delete(self):
        emissionid = self.emission.emissionid

        with self.cli("emissions", "delete", emissionid) as std:
            self.assertFalse(std.out)

        with self.assertUnknownId():
            with self.cli("emissions", "read", emissionid) as std:
                pass

    def test_delete__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("emissions", "delete", self.unknown_id):
                pass
