import contextlib
import pathlib
import tempfile
import unittest

from ldtvouchers import cli


class CliDbTestCase(unittest.TestCase):
    @contextlib.contextmanager
    def _tmpdir(self):
        with tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers", ignore_cleanup_errors=True
        ) as tmpdir:
            yield pathlib.Path(tmpdir)

    def test_init(self):
        with self._tmpdir() as root:
            db = root / "db.sqlite3"

            cli.parse_args(["--db", str(db), "db", "init"])

            self.assertTrue(db.exists())
