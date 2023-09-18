import contextlib
import pathlib
import tempfile
import unittest


class TestCaseMixin:
    @contextlib.contextmanager
    def tmpdir(self):
        with tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers-", ignore_cleanup_errors=True
        ) as tmpdir:
            yield pathlib.Path(tmpdir)


class TestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self._tmpdir = tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers-", ignore_cleanup_errors=True
        )
        self.tmpdir = pathlib.Path(self._tmpdir.name)
        self.dbpath = self.tmpdir / "db.sqlite3"

    def tearDown(self):
        self._tmpdir.cleanup()

        super().tearDown()
