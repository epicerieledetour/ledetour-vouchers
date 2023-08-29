import datetime
import pathlib
import unittest

from ldtvouchers import db


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_initdb(self):
        db.initdb(self.conn)

        sql = (pathlib.Path(__file__).parent / "test_triggers.sql").read_text()
        self.conn.executescript(sql)

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
