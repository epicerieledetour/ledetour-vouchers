import datetime
import pathlib
import unittest

from ldtvouchers import db, models


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.initdb(self.conn)

    def tearDown(self):
        self.conn.close()


class DbInitTestCase(DbTestCase):
    def test_triggers(self):
        # Deterministic tokens are needed in the test script,
        # so our USERID and VOUCHERID custom sqlite functions are
        # temporarily overriden

        def _user_id(userid, userlabel):
            return "tokusr_{}".format(userlabel)

        def _voucher_id(voucherid, emissionid, sortnumber):
            return "tokvch_{}".format(voucherid)

        self.conn.create_function("USERID", 2, _user_id)
        self.conn.create_function("VOUCHERID", 3, _voucher_id)

        sql = (pathlib.Path(__file__).parent / "test_triggers.sql").read_text()
        self.conn.executescript(sql)

        # Test created tokens

        expected_token_rows = (
            {"token": "tokusr_dist", "tablename": "users", "idintable": 1},
            {"token": "tokusr_cashier", "tablename": "users", "idintable": 2},
            {"token": "tokusr_cashier2", "tablename": "users", "idintable": 3},
            {"token": "tokvch_1", "tablename": "vouchers", "idintable": 1},
            {"token": "tokvch_2", "tablename": "vouchers", "idintable": 2},
            {"token": "tokvch_3", "tablename": "vouchers", "idintable": 3},
            {"token": "tokvch_4", "tablename": "vouchers", "idintable": 4},
            {"token": "tokvch_5", "tablename": "vouchers", "idintable": 5},
        )
        for tkn, row in zip(
            expected_token_rows, self.conn.execute("SELECT * FROM tokens")
        ):
            self.assertDictEqual(tkn, dict(**row))

        # Testing final vouchers status

        expected_cashedin_by = (2, None, None, None, 3)
        for by, row in zip(
            expected_cashedin_by, self.conn.execute("SELECT * FROM vouchers")
        ):
            self.assertEqual(by, row["cashedin_by"])
            if by:
                for key in ("cashedin_utc", "undo_expiration_utc"):
                    self.assertTrue(datetime.datetime.fromisoformat(row[key]))

        # Testing action responses

        expected_response_ids = (
            "error_voucher_unauthentified",
            "error_voucher_user_needs_voucher_token",
            "ok_voucher_cashedin",
            "error_voucher_invalid",
            "error_voucher_expired",
            "ok_voucher_info",
            "ok_voucher_cashedin",
            "error_voucher_cannot_undo_not_cashedin",
            "ok_voucher_info",
            "error_voucher_cashedin_by_another_user",
            "warning_voucher_cannot_undo_cashedin",
            "error_voucher_cannot_undo_cashedin",
            "error_system_unexpected_request",
            "warning_voucher_can_undo_cashedin",
            "ok_voucher_cashedin",
            "ok_voucher_undo",
            "error_user_invalid_token",
            "ok_user_authentified",
        )
        for responseid, row in zip(
            expected_response_ids, self.conn.execute("SELECT * FROM actions")
        ):
            self.assertEqual(
                responseid,
                row["responseid"],
                "Error at response id test {actionid}".format(**row),
            )

    def test_token_user(self):
        """Checking that user tokens do not leak user data like userid or label"""

        with self.conn:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO users (label) VALUES ('theUser')")
            userid = cur.lastrowid

        user = self.conn.execute(
            "SELECT * FROM users WHERE userid = ?", (userid,)
        ).fetchone()

        token = self.conn.execute(
            "SELECT * FROM tokens WHERE tablename = 'users' AND idintable = ?",
            (userid,),
        ).fetchone()

        self.assertEqual("users", token["tablename"])
        self.assertEqual(user["userid"], token["idintable"])

        prefix, suffix = token["token"].split("_")
        self.assertEqual(prefix, "tokusr")

        for key in user.keys():
            self.assertNotEqual(
                suffix,
                str(user[key]),
                "Field '{}' is leaking in user token '{}'".format(key, token["token"]),
            )

    def test_token_voucher(self):
        """Checking that voucher tokens are of the form sortnumber-random"""

        with self.conn:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO vouchers (emissionid, sortnumber) VALUES (42, 73)")
            voucherid = cur.lastrowid

        voucher = self.conn.execute(
            "SELECT * FROM vouchers WHERE voucherid = ?", (voucherid,)
        ).fetchone()

        token = self.conn.execute(
            "SELECT * FROM tokens WHERE tablename = 'vouchers' AND idintable = ?",
            (voucherid,),
        ).fetchone()

        sortnumber, randomstring = token["token"].split("-")

        self.assertEqual(voucher["sortnumber"], int(sortnumber))
        self.assertEqual(len(randomstring), 5)
        self.assertTrue(randomstring.isalpha())
        self.assertTrue(randomstring.isupper())


class DbUsersTestCase(DbTestCase):
    def setUp(self):
        super().setUp()

        self.base = models.UserBase(
            label="lbl", can_cashin=True, can_cashin_by_voucherid=True
        )

    def test_create(self):
        new = db.create_user(self.conn, self.base)
        self.assertTrue(new.userid)
        self.assertDictEqual(self.base.model_dump(), new.model_dump(exclude=["userid"]))

    def test_read(self):
        new = db.create_user(self.conn, self.base)
        read = db.read_user(self.conn, new.userid)

        self.assertEqual(new, read)
