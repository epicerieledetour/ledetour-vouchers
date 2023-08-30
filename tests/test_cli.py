import unittest

import testutils
from ldtvouchers import cli


class CliDbTestCase(unittest.TestCase, testutils.TestCaseMixin):
    def test_init(self):
        with self.tmpdir() as root:
            db = root / "db.sqlite3"

            cli.parse_args(["--db", str(db), "db", "init"])

            self.assertTrue(db.exists())
