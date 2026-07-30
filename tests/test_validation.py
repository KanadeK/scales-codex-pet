from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scales_pet.validation import validate_source

from .helpers import make_pet


class ValidationTests(unittest.TestCase):
    def test_valid_v2_package_passes_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet")
            report = validate_source(pet, target_name="desktop", strict=True)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.required_cells, 73)
        self.assertEqual(report.populated_required_cells, 73)
        self.assertEqual(report.unused_cells, 15)
        self.assertEqual(report.empty_unused_cells, 15)

    def test_missing_required_cell_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet", missing=(0, 0))
            report = validate_source(pet, target_name="desktop")

        self.assertFalse(report.ok)
        self.assertIn("required-cell-empty", {issue.code for issue in report.errors})

    def test_populated_unused_cell_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet", populate_unused=(7, 0))
            report = validate_source(pet, target_name="desktop")

        self.assertFalse(report.ok)
        self.assertIn("unused-cell-populated", {issue.code for issue in report.errors})

    def test_edge_touch_is_warning_and_strict_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet", edge=(0, 0))
            relaxed = validate_source(pet, target_name="desktop")
            strict = validate_source(pet, target_name="desktop", strict=True)

        self.assertTrue(relaxed.ok)
        self.assertFalse(strict.ok)
        self.assertIn("cell-edge-touch", {issue.code for issue in strict.warnings})

    def test_wrong_target_reports_dimension_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet")
            report = validate_source(pet, target_name="web")

        self.assertFalse(report.ok)
        self.assertIn("target-dimensions", {issue.code for issue in report.errors})


if __name__ == "__main__":
    unittest.main()
