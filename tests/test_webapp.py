import datetime
from http import HTTPStatus

import testutils
from fastapi.testclient import TestClient
from ldtvouchers import db, models, webapp

{
    "status": {
        "level": "warning",
        "description": "Voucher already cashed",
    },
    "user": {},
    "voucher": {
        "token": "AJCG-4564",
        "value": 20,
        "cashedin_by": "The User Description",
        "cashedin_localtime": "2023-09-12T13:00:31",
        "undo_expiration_localtime": "1970-00-00",
        "history": [
            {
                "action": "scan",
                "user_label": "usr1",
            }
        ],
    },
}

# action url
# - unknown
# - scan
# - undo

# Auth header
# - None
# - Malformed
# - Unknown user
# - Valid user

# scan url_token
# - None
# - malformed
# - Unkown token
# - Valid user
# - Valid voucher

# Voucher expired
# - no
# - yes

# Voucher cashed in
# - no
# - by current user
# - by another user

# User can cashin / undo
# - no
# - yes

# Voucher current time withing timeout
# - no
# - yes


class WebAppTestCase(testutils.TestCase):
    def setUp(self):
        super().setUp()

        webapp.get_db.dbpath = self.dbpath
        self.client = TestClient(webapp.app)

        with db.connect(self.dbpath) as conn:
            db.initdb(conn)

            self.cashier1 = db.create_user(
                conn,
                models.UserBase(
                    label="cashier1",
                    description="cashier1 description",
                    can_cashin=True,
                ),
            )
            self.public_cashier1 = db.read_public_user(conn, self.cashier1.userid)
            self.headers_cashier1 = {
                "Authorization": "Bearer {}".format(self.public_cashier1.token)
            }

            self.cashier2 = db.create_user(
                conn,
                models.UserBase(
                    label="cashier2",
                    description="cashier2 description",
                    can_cashin=True,
                ),
            )
            self.public_cashier2 = db.read_public_user(conn, self.cashier2.userid)
            self.headers_cashier2 = {
                "Authorization": "Bearer {}".format(self.public_cashier2.token)
            }

            self.distributor = db.create_user(
                conn,
                models.UserBase(
                    label="distributor",
                    description="distributor description",
                    can_cashin=False,
                ),
            )

            self.now = datetime.datetime.utcnow()
            self.expiration_timedelta = datetime.timedelta(90)

            self.emission1 = db.create_emission(
                conn,
                models.EmissionBase(
                    label="emission1",
                    expiration_utc=self.now + self.expiration_timedelta,
                ),
            )

            with db.set_emission_vouchers(
                conn, self.emission1.emissionid
            ) as add_voucher:
                add_voucher(
                    models.VoucherImport(
                        value_CAN=1, distributed_by_label=self.distributor.label
                    )
                )
                add_voucher(
                    models.VoucherImport(
                        value_CAN=2, distributed_by_label=self.distributor.label
                    )
                )

            self.emission1 = db.read_public_emission(conn, self.emission1.emissionid)
            self.voucher1, self.voucher2 = self.emission1.vouchers

            # self.url_scan_cashier1 = "/scan/{}".format(self.public_cashier1.token)
            # self.url_scan_cashier2 = "/scan/{}".format(self.public_cashier2.token)
            # self.url_scan_voucher1 = "/scan/{}".format(self.voucher1.token)
            # self.url_undo_voucher1 = "/undo/{}".format(self.voucher1.token)
            # self.url_scan_voucher2 = "/scan/{}".format(self.voucher2.token)
            # self.url_undo_voucher2 = "/undo/{}".format(self.voucher2.token)

    def request(self, action="", usertoken="", vouchertoken=""):
        elems = [el for el in ("u", action, usertoken, vouchertoken) if el]
        url = "/".join(elems)
        return self.get(url)

    def scan(self, *args):
        return self.request("scan", *args)

    def undo(self, *args):
        return self.request("undo", *args)

    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)
        # return resp.status_code, models.HttpResponse(**resp.json())

    def test_invalid_action_url(self):
        resp = self.get("/this/endpoint/does/not/exist")

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        self.assertDictEqual(resp.json(), {"detail": "Not Found"})

    def test_start_page(self):
        resp = self.get("/")

        self.assertEqual(resp.status_code, HTTPStatus.OK)

    # 1
    def test_error_voucher_unauthentified(self):
        resp = self.scan(
            "invalid_user_token",
            self.voucher1.token,
        )

        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

    # 2
    def test_error_voucher_user_needs_voucher_token(self):
        pass

    # 3
    def test_error_voucher_invalid(self):
        pass

    # 4
    def test_error_voucher_expired(self):
        pass

    def assertAlmostNow(self, date):
        return date - datetime.datetime.utcnow() < datetime.timedelta(seconds=1.0)

    def assertLater(self, date):
        return date - datetime.datetime.utcnow() > datetime.timedelta(minutes=1.0)

    # 5
    def test_ok_voucher_cashedin(self):
        pass
        # resp = self.scan(
        #     self.public_cashier1.token,
        #     self.voucher1.token,
        # )

        # self.assertEqual(resp.status_code, HTTPStatus.OK)

        # self.assertEqual(resp.status.level, "ok")
        # self.assertEqual(resp.user, self.public_cashier1)

        # self.assertEqual(resp.voucher.token, self.voucher1.token)
        # self.assertEqual(resp.voucher.value_CAN, self.voucher1.value_CAN)
        # self.assertEqual(resp.voucher.cashedin_by_label, self.cashier1.label)
        # self.assertEqual(
        #     resp.voucher.cashedin_by_description, self.cashier1.description
        # )
        # self.assertAlmostNow(resp.voucher.cashedin_utc)
        # self.assertLater(resp.voucher.undo_expiration_utc)

        # self.assertEqual(len(resp.voucher.history), 1)
        # self.assertEqual(
        #     resp.voucher.history[0],
        #     models.HttpAction(
        #         timestamp_utc=resp.voucher.cashedin_utc,
        #         user_label=self.cashier1.label,
        #         user_description=self.cashier1.description,
        #         requestid="scan",
        #         responseid="ok_voucher_cashedin",
        #     ),
        # )

    # 6
    def test_error_voucher_cashedin_by_another_user(self):
        pass

    # 7
    def test_warning_voucher_cannot_undo_cashedin(self):
        pass

    # 8
    def test_warning_voucher_can_undo_cashedin(self):
        pass

    # 9
    def test_error_user_invalid_token(self):
        resp = self.scan(
            "invalid_user_token",
        )

        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

    # 10
    def test_ok_user_authentified(self):
        resp = self.scan(
            self.public_cashier1.token,
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)

        # self.assertEqual(resp.status.level, "ok")
        # self.assertEqual(resp.user, self.public_cashier1)
        # self.assertIsNone(resp.voucher)

    # 11
    def test_ok_voucher_info(self):
        pass

    # 12
    def test_error_voucher_cannot_undo_cashedin(self):
        pass

    # 13
    def test_error_bad_request(self):
        resp = self.request(
            "invalid_action_verb",
            "user_not_important_for_this_test",
            "voucher_not_important_for_this_test",
        )

        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    # 14
    def test_ok_voucher_undo(self):
        pass

    # 15
    def test_error_voucher_cannot_undo_not_cashedin(self):
        pass
