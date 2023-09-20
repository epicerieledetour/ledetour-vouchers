import datetime

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

    def test_emission_vouchers(self):
        emissionid = 1
        vouchers = []
        for i in range(21):
            vouchers.append(
                models.PublicVoucher(
                    token=f"{i:04d}-RAND",
                    emissionid=emissionid,
                    value_CAN=(i % 3) * 5,
                    sortnumber=i,
                )
            )

        emission = models.PublicEmission(
            expiration_utc=datetime.datetime.utcnow(),
            vouchers=vouchers,
        )
        path = self.tmpdir / "vouchers.pdf"

        with path.open("wb") as fp:
            gen.emission_vouchers(emission, fp)

        # TODO: check content, no just existence
        self.assertTrue(path.exists())
