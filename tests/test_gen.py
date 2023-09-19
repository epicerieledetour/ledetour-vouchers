import testutils
from ldtvouchers import gen, models


class GenTestCase(testutils.TestCase):
    def test_user_authpage(self):
        user = models.PublicUser(token="some_token_for_user1", label="USR1")
        path = self.tmpdir / "user.pdf"

        with path.open("wb") as fp:
            gen.user_authpage(user, fp)

        # TODO: check content, no just existence
        self.assertTrue(path.exists())
