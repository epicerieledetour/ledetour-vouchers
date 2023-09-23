import datetime
import json
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import odf.opendocument
import testutils
from ldtvouchers import cli, db, models


class _Std:
    def __init__(self, outio=None, errio=None):
        self.errio = StringIO() if outio is None else outio
        self.outio = StringIO() if errio is None else errio

    #    @property
    #    def err(self):
    #        return self.errio.getvalue()

    @property
    def out(self):
        return self.outio.getvalue()

    @property
    def outlines(self):
        return self.out.split("\n")

    def load(self, model):
        return model(**json.loads(self.out))

    def validate(self, model):
        model.validate(json.loads(self.out))


class CliTestCase(testutils.TestCase):
    unknown_id = 42

    def setUp(self):
        super().setUp()

        with self.cli("db", "init"):
            pass

    @contextmanager
    def cli(self, *args, outio=None, errio=None):
        std = _Std()
        with redirect_stderr(std.errio), redirect_stdout(std.outio):
            cli.parse_args(["--db", str(self.dbpath)] + [str(arg) for arg in args])
            yield std

    @contextmanager
    def assertUnknownId(self):
        with self.assertRaises(SystemExit) as cm:
            yield

        err = cm.exception.args[0]

        self.assertTrue(isinstance(err, db.UnknownId))
        self.assertRegex(str(err), r"^Unknown \w+ .+$")


class CliDbTestCase(unittest.TestCase, testutils.TestCaseMixin):
    def test_init(self):
        with self.tmpdir() as root:
            db = root / "db.sqlite3"

            cli.parse_args(["--db", str(db), "db", "init"])

            self.assertTrue(db.exists())


class CliUsersTestCase(CliTestCase):
    def test_create__no_argument(self):
        with self.cli("users", "create") as std:
            std.validate(models.User)

    def test_create(self):
        label = "testuser"
        can_cashin = True
        with self.cli(
            "users", "create", "--label", label, "--can_cashin", can_cashin
        ) as std:
            user = std.load(models.User)
            self.assertEqual(user.label, label)
            self.assertTrue(user.can_cashin)
            self.assertFalse(user.can_cashin_by_voucherid)

    def test_read(self):
        with self.cli("users", "create") as std:
            created = std.load(models.User)

        with self.cli("users", "read", created.userid) as std:
            read = std.load(models.User)

        self.assertEqual(created, read)

    def test_read__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "read", self.unknown_id):
                pass  # pragma: no cover

    def test_list(self):
        with self.cli("users", "create") as std:
            user1 = std.load(models.User)

        with self.cli("users", "create") as std:
            user2 = std.load(models.User)

        with self.cli("users", "list") as std:
            line1, line2, _ = std.outlines

            self.assertIn(str(user1.userid), line1)
            self.assertIn(str(user2.userid), line2)

    def test_update(self):
        with self.cli("users", "create") as std:
            user = std.load(models.User)
            self.assertEqual(user.label, "")

        userid = user.userid
        label = "userLabel"

        with self.cli("users", "update", userid, "--label", label) as std:
            user = std.load(models.User)
            self.assertEqual(user.userid, userid)
            self.assertEqual(user.label, label)

    def test_update__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "update", self.unknown_id, "--label", "lbl"):
                pass  # pragma: no cover

    def test_delete(self):
        with self.cli("users", "create") as std:
            user = std.load(models.User)
            userid = user.userid

        with self.cli("users", "delete", userid) as std:
            self.assertFalse(std.out)

        with self.assertUnknownId():
            with self.cli("users", "read", userid) as std:
                pass  # pragma: no cover

    def test_delete__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "delete", self.unknown_id):
                pass  # pragma: no cover


class EmissionsTestCase(CliTestCase):
    def setUp(self):
        super().setUp()

        with self.cli("emissions", "create") as std:
            self.emission = std.load(models.Emission)

        with self.cli("users", "create", "--label", "user1") as std:
            self.user1 = std.load(models.User)

        with self.cli("users", "create", "--label", "user2") as std:
            self.user2 = std.load(models.User)

        self.csvpath = Path(__file__).parent / "test_import.csv"

    def test_create__empty(self):
        with self.cli("emissions", "create") as std:
            emission = std.load(models.Emission)

            self.assertIsInstance(emission, models.Emission)

    def test_create(self):
        label = "emissionLabel"
        expiration_str = "2042-12-31"
        expiration_utc = datetime.datetime.fromisoformat(expiration_str)

        with self.cli(
            "emissions", "create", "--expiration_utc", expiration_str, "--label", label
        ) as std:
            emission = std.load(models.Emission)

            self.assertEqual(emission.label, label)
            self.assertEqual(emission.expiration_utc, expiration_utc)

    def test_read(self):
        with self.cli("emissions", "read", self.emission.emissionid) as std:
            emission = std.load(models.Emission)

        self.assertEqual(self.emission, emission)

    def test_read__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("emissions", "read", self.unknown_id):
                pass  # pragma: no cover

    def test_list(self):
        with self.cli("emissions", "create") as std:
            emission = std.load(models.Emission)

        with self.cli("emissions", "list") as std:
            line1, line2, _ = std.outlines

            self.assertIn(str(self.emission.emissionid), line1)
            self.assertIn(str(emission.emissionid), line2)

    def test_update(self):
        label = "emissionLabel"

        with self.cli(
            "emissions", "update", self.emission.emissionid, "--label", label
        ) as std:
            emission = std.load(models.Emission)

            self.emission.label = label

            self.assertEqual(self.emission, emission)

    def test_update__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("users", "update", self.unknown_id, "--label", "lbl"):
                pass  # pragma: no cover

    def test_delete(self):
        emissionid = self.emission.emissionid

        with self.cli("emissions", "delete", emissionid) as std:
            self.assertFalse(std.out)

        with self.assertUnknownId():
            with self.cli("emissions", "read", emissionid) as std:
                pass  # pragma: no cover

    def test_delete__unknown_id(self):
        with self.assertUnknownId():
            with self.cli("emissions", "delete", self.unknown_id):
                pass  # pragma: no cover

    def test_import(self):
        with self.cli(
            "emissions", "import", self.emission.emissionid, str(self.csvpath)
        ) as std:
            emission = std.load(models.Emission)

            self.emission.vouchers = [
                models.Voucher(
                    voucherid=1,
                    emissionid=self.emission.emissionid,
                    value_CAN=11,
                    sortnumber=1,
                    distributed_by=1,
                ),
                models.Voucher(
                    voucherid=2,
                    emissionid=self.emission.emissionid,
                    value_CAN=12,
                    sortnumber=2,
                    distributed_by=2,
                ),
            ]
            self.assertEqual(self.emission, emission)

    def test_import__idempotency(self):
        emissions = []

        for _ in range(2):
            with self.cli(
                "emissions", "import", self.emission.emissionid, str(self.csvpath)
            ) as std:
                emissions.append(std.load(models.Emission))

        emissions1, emissions2 = emissions

        self.assertEqual(emissions1, emissions2)


class FullDBTestCase(CliTestCase):
    def setUp(self):
        super().setUp()

        # Users

        with self.cli(
            "users",
            "create",
            "--label",
            "user1",
        ) as std:
            self.user_dist1 = std.load(models.User)

        with self.cli(
            "users",
            "create",
            "--label",
            "user2",
        ) as std:
            self.user_dist2 = std.load(models.User)

        with self.cli(
            "users",
            "create",
            "--label",
            "user3",
            "--can_cashin",
            "true",
            "--can_cashin_by_voucherid",
            "true",
        ) as std:
            self.user_scan1 = std.load(models.User)

        self.user = self.user_scan1

        # Emission

        with self.cli(
            "emissions",
            "create",
            "--label",
            "EmissionLabel",
            "--expiration_utc",
            "2042-12-31",
        ) as std:
            self.emission = std.load(models.Emission)

        csvpath = Path(__file__).parent / "test_import.csv"

        with self.cli(
            "emissions",
            "import",
            self.emission.emissionid,
            str(csvpath),
        ) as std:
            self.emission = std.load(models.Emission)

        self.voucher1, self.voucher2 = self.emission.vouchers
        self.voucher = self.voucher1


class ActionsTestCase(FullDBTestCase):
    def test_scan__voucher_by_id(self):
        with self.cli(
            "actions",
            "scan",
            "--userid",
            self.user.userid,
            "--voucherid",
            self.voucher.voucherid,
        ):
            pass

        with self.cli("emissions", "read", self.emission.emissionid) as std:
            emission = std.load(models.Emission)

        voucher = emission.vouchers[0]

        self.assertEqual(voucher.distributed_by, self.user_dist1.userid)
        self.assertEqual(voucher.cashedin_by, self.user.userid)
        self.assertIsInstance(voucher.cashedin_utc, datetime.datetime)

    def test_undo(self):
        with self.cli(
            "actions",
            "scan",
            "--userid",
            self.user.userid,
            "--voucherid",
            self.voucher.voucherid,
        ):
            pass

        with self.cli(
            "actions",
            "undo",
            "--userid",
            self.user.userid,
            "--voucherid",
            self.voucher.voucherid,
        ):
            pass

        with self.cli("emissions", "read", self.emission.emissionid) as std:
            emission = std.load(models.Emission)

        voucher = emission.vouchers[0]

        self.assertEqual(voucher, self.emission.vouchers[0])


class GenerateTestCase(FullDBTestCase):
    def setUp(self):
        super().setUp()

        with self.cli(
            "actions",
            "scan",
            "--userid",
            self.user_scan1.userid,
        ):
            pass

        with self.cli(
            "actions",
            "scan",
            "--voucherid",
            self.voucher1.voucherid,
            "--userid",
            self.user_scan1.userid,
        ):
            pass

        with self.cli(
            "actions",
            "scan",
            "--userid",
            self.user_dist1.userid,
        ):
            pass

        with self.cli(
            "actions",
            "scan",
            "--voucherid",
            self.voucher1.voucherid,
            "--userid",
            self.user_dist1.userid,
        ):
            pass

        with self.cli(
            "actions",
            "scan",
            "--userid",
            self.user_dist2.userid,
        ):
            pass

        with self.cli(
            "actions",
            "scan",
            "--voucherid",
            self.voucher2.voucherid,
            "--userid",
            self.user_dist2.userid,
        ):
            pass

        with self.cli(
            "actions",
            "undo",
            "--voucherid",
            self.voucher2.voucherid,
            "--userid",
            self.user_scan1.userid,
        ):
            pass

    def test_authpage(self):
        path = self.tmpdir / "user.pdf"

        with self.cli("users", "authpage", self.user.userid, path):
            self.assertTrue(path.exists())

    def test_authpage__unknown_id(self):
        path = self.tmpdir / "user.pdf"
        with self.assertUnknownId():
            with self.cli("users", "authpage", self.unknown_id, path):
                pass  # pragma: no cover

    def test_vouchers(self):
        path = self.tmpdir / "vouchers.pdf"

        with self.cli("emissions", "vouchers", self.emission.emissionid, path):
            pass

    def test_vouchers__unknown_id(self):
        path = self.tmpdir / "vouchers.pdf"

        with self.assertUnknownId():
            with self.cli("emissions", "vouchers", self.unknown_id, path):
                pass  # pragma: no cover

    def test_emission_htmlreport(self):
        path = self.tmpdir / "vouchers.pdf"

        with self.cli("emissions", "htmlreport", self.emission.emissionid, path):
            pass

    def test_emission_odsreport(self):
        path = self.tmpdir / "report.ods"

        with self.cli("emissions", "odsreport", path):
            pass

        odf.opendocument.load(path)

    def test_emission_remailreport(self):
        # TODO: better test
        with self.cli("debug", "filldb"):
            pass

        with self.cli("emissions", "emailreport"):
            pass
