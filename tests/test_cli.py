import json
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import testutils
from ldtvouchers import cli, models


class _Std:
    def __init__(self):
        self.errio = StringIO()
        self.outio = StringIO()

    # @property
    # def err(self):
    #     return self.errio.getvalue()

    @property
    def out(self):
        return self.outio.getvalue()

    def load(self, model):
        return model(**json.loads(self.out))

    def validate(self, model):
        model.validate(json.loads(self.out))


class CliDbTestCase(unittest.TestCase, testutils.TestCaseMixin):
    def test_init(self):
        with self.tmpdir() as root:
            db = root / "db.sqlite3"

            cli.parse_args(["--db", str(db), "db", "init"])

            self.assertTrue(db.exists())


class CliUsersTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self._tmpdir = tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers", ignore_cleanup_errors=True
        )
        self.tmpdir = Path(self._tmpdir.name)
        self.dbpath = self.tmpdir / "db.sqlite3"

        with self.cli("db", "init"):
            pass

    def tearDown(self):
        self._tmpdir.cleanup()

        super().tearDown()

    @contextmanager
    def cli(self, *args):
        std = _Std()
        with redirect_stderr(std.errio), redirect_stdout(std.outio):
            cli.parse_args(["--db", str(self.dbpath)] + [str(arg) for arg in args])
            yield std

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
