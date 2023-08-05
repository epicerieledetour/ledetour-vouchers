import datetime
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


# TODO: make _ret_lines public
def _ret_lines(process: subprocess.CompletedProcess) -> list[str]:
    lines = process.stdout.decode().split("\n")
    return lines[:-1]


class TestCase(unittest.TestCase):
    root_path = None

    @classmethod
    def setUpClass(cls):
        cls.root_path = pathlib.Path(
            tempfile.mkdtemp(
                prefix=f"ldt-vouchers-test-{datetime.datetime.now().isoformat()}"
            )
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
