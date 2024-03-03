import datetime
from http import HTTPStatus
from xml.etree import ElementTree as ET

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

        webapp.app.dependency_overrides[webapp.get_settings] = (
            self.get_settings_override
        )
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
            self.public_distributor = db.read_public_user(conn, self.distributor.userid)

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

            self.emission1 = db.read_emission(conn, self.emission1.emissionid)
            self.cashier1_token = self.public_cashier1.token
            self.cashier2_token = self.public_cashier2.token
            self.distributor_token = self.public_distributor.token

            self.voucher1, self.voucher2 = self.emission1.vouchers
            self.voucher1_token, self.voucher2_token = [
                voucher.token
                for voucher in db._read_public_vouchers(conn, self.emission1.emissionid)
            ]

            # self.url_scan_cashier1 = "/scan/{}".format(self.public_cashier1.token)
            # self.url_scan_cashier2 = "/scan/{}".format(self.public_cashier2.token)
            # self.url_scan_voucher1 = "/scan/{}".format(self.voucher1.token)
            # self.url_undo_voucher1 = "/undo/{}".format(self.voucher1.token)
            # self.url_scan_voucher2 = "/scan/{}".format(self.voucher2.token)
            # self.url_undo_voucher2 = "/undo/{}".format(self.voucher2.token)

    def get_settings_override(self) -> webapp.Settings:
        return webapp.Settings(dbpath=self.dbpath)

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

    def set_vouchers_undo_expiration_to_the_past(self):
        with db.connect(self.dbpath) as conn:
            conn.execute(
                "UPDATE vouchers SET undo_expiration_utc = '1970-01-01 00:00:01'"
            )

    def test_invalid_action_url(self):
        resp = self.get("/this/endpoint/does/not/exist")

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        self.assertDictEqual(resp.json(), {"detail": "Not Found"})

    def test_start_page(self):
        resp = self.get("/")

        self.assertResponse(resp, HTTPStatus.OK, "None")

    # 1
    def test_error_voucher_unauthentified(self):
        resp = self.scan("invalid_user_token", self.voucher1_token)

        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

    # 2
    def test_error_voucher_user_needs_voucher_token(self):
        pass

    # 3
    def test_error_voucher_invalid(self):
        resp = self.scan(self.cashier1_token, "invalid_voucher_token")

        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    # 4
    def test_error_voucher_expired(self):
        with db.connect(self.dbpath) as conn:
            self.emission1.expiration_utc -= self.expiration_timedelta * 2
            db.update_emission(conn, self.emission1)

        resp = self.scan(self.cashier1_token, self.voucher1_token)

        self.assert_(resp.status_code, HTTPStatus.FORBIDDEN)

    def assertAlmostNow(self, date):
        return date - datetime.datetime.utcnow() < datetime.timedelta(seconds=1.0)

    def assertLater(self, date):
        return date - datetime.datetime.utcnow() > datetime.timedelta(minutes=1.0)

    # 5
    def test_ok_voucher_cashedin(self):
        resp = self.scan(self.cashier1_token, self.voucher1_token)

        self.assertResponse(resp, HTTPStatus.OK, "ok_voucher_cashedin")

    # 6
    def test_error_voucher_cashedin_by_another_user(self):
        self.scan(self.cashier1_token, self.voucher1_token)
        resp = self.scan(self.cashier2_token, self.voucher1_token)

        self.assertResponse(
            resp, HTTPStatus.FORBIDDEN, "error_voucher_cashedin_by_another_user"
        )

    # 7
    def test_warning_voucher_cannot_undo_cashedin(self):
        self.scan(self.cashier1_token, self.voucher1_token)

        self.set_vouchers_undo_expiration_to_the_past()

        resp = self.scan(self.cashier1_token, self.voucher1_token)

        self.assertResponse(resp, HTTPStatus.OK, "warning_voucher_cannot_undo_cashedin")

    # 8
    def test_warning_voucher_can_undo_cashedin(self):
        self.scan(self.cashier1_token, self.voucher1_token)
        resp = self.scan(self.cashier1_token, self.voucher1_token)

        self.assertResponse(resp, HTTPStatus.OK, "warning_voucher_can_undo_cashedin")

    # 9
    def test_error_user_invalid_token(self):
        pass
        # resp = self.scan(
        #     "invalid_user_token",
        # )

        # self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

    # 10
    def test_ok_user_authentified(self):
        resp = self.scan(
            self.public_cashier1.token,
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)

        # self.assertEqual(resp.status.level, "ok")
        # self.assertEqual(resp.user, self.public_cashier1)
        # self.assertIsNone(resp.voucher)

    def assertResponse(self, resp, status_code, responseid):
        self.assertEqual(resp.status_code, status_code)

        html = ET.fromstring(resp.content.decode())
        meta = html.find(".//meta[@name='responseid']")
        self.assertEqual(meta.attrib.get("content"), responseid)

    # 11
    def test_ok_voucher_info(self):
        resp = self.scan(self.distributor_token, self.voucher1_token)

        self.assertResponse(resp, HTTPStatus.OK, "ok_voucher_info")

    # 12
    def test_error_voucher_cannot_undo_cashedin(self):
        self.scan(self.cashier1_token, self.voucher1_token)
        self.set_vouchers_undo_expiration_to_the_past()
        resp = self.undo(self.cashier1_token, self.voucher1_token)

        self.assertResponse(
            resp, HTTPStatus.FORBIDDEN, "error_voucher_cannot_undo_cashedin"
        )

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
        self.scan(self.cashier1_token, self.voucher1_token)
        resp = self.undo(self.cashier1_token, self.voucher1_token)

        self.assertResponse(resp, HTTPStatus.OK, "ok_voucher_undo")

    # 15
    def test_error_voucher_cannot_undo_not_cashedin(self):
        resp = self.undo(self.cashier1_token, self.voucher1_token)

        self.assertResponse(
            resp, HTTPStatus.FORBIDDEN, "error_voucher_cannot_undo_not_cashedin"
        )
