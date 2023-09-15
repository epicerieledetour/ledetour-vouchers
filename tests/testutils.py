import contextlib
import pathlib
import tempfile


class TestCaseMixin:
    @contextlib.contextmanager
    def tmpdir(self):
        with tempfile.TemporaryDirectory(
            prefix="test-ldtvouchers-", ignore_cleanup_errors=True
        ) as tmpdir:
            yield pathlib.Path(tmpdir)
