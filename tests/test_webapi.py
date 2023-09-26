import testutils

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


class WebAPITestCase(testutils.TestCase):
    # 1
    def test_error_voucher_unauthentified(self):
        pass

    # 2
    def test_error_voucher_user_needs_voucher_token(self):
        pass

    # 3
    def test_error_voucher_invalid(self):
        pass

    # 4
    def test_error_voucher_expired(self):
        pass

    # 5
    def test_ok_voucher_cashedin(self):
        pass

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
        pass

    # 10
    def test_ok_user_authentified(self):
        pass

    # 11
    def test_ok_voucher_info(self):
        pass

    # 12
    def test_error_voucher_cannot_undo_cashedin(self):
        pass

    # 13
    def test_error_system_unexpected_request(self):
        pass

    # 14
    def test_ok_voucher_undo(self):
        pass

    # 15
    def test_error_voucher_cannot_undo_not_cashedin(self):
        pass
