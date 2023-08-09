import csv
import json
import subprocess

from app.events import models as events_models
from app.emissions import models as emissions_models

from .utils import _ret_lines, TestCase


class EmissionsCliTestCase(TestCase):
    # Create

    def test_create__empty(self):
        ids = _ret_lines(
            self.run_cli(
                "emissions",
                "create",
            )
        )
        lines = _ret_lines(self.run_cli("emissions", "read", *ids))

        for id, line in zip(ids, lines):
            self.assertTrue(id in line)

    def test_create__with_args(self):
        ids = _ret_lines(
            self.run_cli(
                "emissions",
                "create",
                "--label",
                "emission0",
                "--description",
                "The new emission description",
                "--expiration_utc",
                "2023-12-31T23:59:59-06:00",
            )
        )
        lines = _ret_lines(self.run_cli("emissions", "read", *ids))

        self.assertTrue("emission0" in lines[0])
        self.assertTrue("The new emission description" in lines[0])
        self.assertTrue("2023-12-31T23:59:59-06:00" in lines[0])

    # Read

    def test_read(self):
        expected_emission_fields = (
            {"label": "emission0", "description": "Description of emission0"},
            {"label": "emission1", "description": "Description of emission1"},
            {"label": "emission2", "description": "Description of emission2"},
        )

        ids = []
        for fields in expected_emission_fields:
            ids.extend(
                _ret_lines(
                    self.run_cli(
                        "emissions",
                        "create",
                        "--label",
                        fields["label"],
                        "--description",
                        fields["description"],
                    )
                )
            )

        lines = _ret_lines(self.run_cli("emissions", "read", *ids))
        dicts = (json.loads(line) for line in lines)
        dicts = sorted(dicts, key=lambda d: d["label"])

        for expected_fields, fields in zip(expected_emission_fields, dicts):
            emission = emissions_models.Emission(**fields)
            for name, value in expected_fields.items():
                self.assertEqual(getattr(emission, name), value)

    def test_read__unknown_id(self):
        with self.assertRaises(subprocess.CalledProcessError):
            _ret_lines(self.run_cli("emissions", "read", "unknown_id"))

    # List

    def test_list(self):
        ids = []

        for _ in range(3):
            ids.extend(_ret_lines(self.run_cli("emissions", "create")))

        lines = self.run_cli("emissions", "list").stdout.decode()

        # TODO: preserve creation order when listing emissions

        for id in ids:
            self.assertTrue(id in lines)

    # Update

    def test_update(self):
        label = "theLabel"
        description = "The description"

        ids = _ret_lines(self.run_cli("emissions", "create", "--label", label))
        id = ids[0]

        self.run_cli("emissions", "update", id, "--description", description)

        lines = self.run_cli("emissions", "read", id).stdout
        emission = emissions_models.Emission(**json.loads(lines.decode()))

        self.assertEqual(emission.label, label)
        self.assertEqual(emission.description, description)

    def test_update__no_args_silently_succeeds(self):
        ids = _ret_lines(self.run_cli("emissions", "create"))
        id = ids[0]

        self.run_cli("emissions", "update", id)

        lines = self.run_cli("emissions", "read", id).stdout
        emission = emissions_models.Emission(**json.loads(lines.decode()))

        self.assertIsNone(emission.label)
        self.assertIsNone(emission.description)

    # Delete

    def test_delete(self):
        ids = []
        for _ in range(3):
            ids.extend(_ret_lines(self.run_cli("emissions", "create")))

        self.run_cli("emissions", "delete", ids[0], ids[2])

        lines = self.run_cli("emissions", "list").stdout.decode()

        self.assertNotIn(ids[0], lines)
        self.assertIn(ids[1], lines)
        self.assertNotIn(ids[2], lines)

    # History

    def test_history(self):
        ids = _ret_lines(self.run_cli("emissions", "create"))
        ids.extend(_ret_lines(self.run_cli("emissions", "create")))

        id0, id1 = ids

        self.run_cli("emissions", "update", "--label", "label_mistake", id1)
        self.run_cli(
            "emissions", "update", "--label", "emission0", "--description", "desc0", id0
        )
        self.run_cli(
            "emissions",
            "update",
            "--label",
            "emission1",
            "--description",
            "desc1",
            "--expiration_utc",
            "2023-12-31T23:59:59-06:00",
            id1,
        )

        lines = _ret_lines(self.run_cli("emissions", "history", id1))

        expected = (
            (events_models._EVENT_CREATE, None, None),
            (events_models._EVENT_UPDATE, "label", None),
            (events_models._EVENT_UPDATE, "description", None),
            (events_models._EVENT_UPDATE, "expiration_utc", None),
            (events_models._EVENT_UPDATE, "deleted", "0"),
            (events_models._EVENT_UPDATE, "label", "label_mistake"),
            (events_models._EVENT_UPDATE, "label", "emission1"),
            (events_models._EVENT_UPDATE, "description", "desc1"),
            (
                events_models._EVENT_UPDATE,
                "expiration_utc",
                "2023-12-31 23:59:59-06:00",
            ),
        )
        for line, (commandid, field, value) in zip(lines, expected):
            data = json.loads(line)
            self.assertEqual(data["commandid"], commandid)
            self.assertEqual(data["field"], field)
            self.assertEqual(data["value"], value)

    # Import / export

    def test_export__empty(self):
        csvpath = self.testdir / "export.csv"

        ids = _ret_lines(self.run_cli("emissions", "create"))
        id = ids[0]

        self.run_cli("emissions", "export", id, str(csvpath))

        with csvpath.open("r") as fp:
            reader = csv.DictReader(fp)

            # TODO: warn before updating ongoing distribution, add start_date

            self.assertListEqual(
                reader.fieldnames,
                ["voucher_index", "voucher_value_CAD", "distributor_label"],
            )

    def test_import__all_new(self):
        importpath = self.testdir / "import.csv"
        exportpath = self.testdir / "export.csv"

        content = """voucher_index,voucher_value_CAD,distributor_label
1,20,Dist1
2,30,Dist2
4,30,Dist1"""

        importpath.write_text(content)

        ids = _ret_lines(self.run_cli("emissions", "create"))
        id = ids[0]

        self.run_cli("users", "create", "--label", "Dist1")
        self.run_cli("users", "create", "--label", "Dist2")

        self.run_cli("emissions", "import", id, str(importpath))

        self.run_cli("emissions", "export", id, str(exportpath))

        with exportpath.open("r") as fp:
            reader = csv.DictReader(fp)

            self.assertDictEqual(
                next(reader),
                {
                    "voucher_index": "1",
                    "voucher_value_CAD": "20",
                    "distributor_label": "Dist1",
                },
            )
            self.assertDictEqual(
                next(reader),
                {
                    "voucher_index": "2",
                    "voucher_value_CAD": "30",
                    "distributor_label": "Dist2",
                },
            )
                        self.assertDictEqual(
                next(reader),
                {
                    "voucher_index": "4",
                    "voucher_value_CAD": "30",
                    "distributor_label": "Dist1",
                },
            )

    def test_import__update_and_new(self):
        pass

    def test_import__fail_and_rollback(self):
        # _if_some_indexes_are_duplicated
        # if an user does not exist
        # if emissionid does not exist
        pass

    def test_import_redistributed(self):
        # Test if distributed by A,then redistributed by B
        pass


    def test_complicated(self):
        # Distributed by A
        # Re distributed by B
        # Scanned by C
        # Cancelled scan by C
        # Scanned by D
