from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scales_pet.install import (
    list_backups,
    resolve_codex_home,
    rollback_pet,
    uninstall_pet,
)
from scales_pet.model import (
    TARGETS,
    direction_cell,
    infer_target,
    resolve_asset,
    row_by_name,
)
from scales_pet.provenance import verify_provenance
from scales_pet.scenario import load_scenario, scenario_frames, validate_scenario

from .helpers import make_pet


class ModelEdgeTests(unittest.TestCase):
    def test_target_state_and_direction_errors_are_explicit(self) -> None:
        self.assertIsNone(infer_target((1, 1)))
        self.assertEqual(row_by_name("wake").name, "waving")
        self.assertEqual(direction_cell("337.5"), (7, 10))
        with self.assertRaises(KeyError):
            row_by_name("not-a-state")
        with self.assertRaises(KeyError):
            direction_cell("12")

    def test_asset_resolver_rejects_missing_and_escaping_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                resolve_asset(root / "missing")

            empty = root / "empty"
            empty.mkdir()
            with self.assertRaises(FileNotFoundError):
                resolve_asset(empty)

            wrong = root / "atlas.gif"
            wrong.write_bytes(b"gif")
            with self.assertRaises(ValueError):
                resolve_asset(wrong)

            pet = root / "pet"
            pet.mkdir()
            (pet / "pet.json").write_text(
                json.dumps({"spritesheetPath": "../outside.webp"}),
                encoding="utf-8",
            )
            (root / "outside.webp").write_bytes(b"outside")
            with self.assertRaises(ValueError):
                resolve_asset(pet)

            (pet / "pet.json").write_text(
                json.dumps({"spritesheetPath": "missing.webp"}),
                encoding="utf-8",
            )
            with self.assertRaises(FileNotFoundError):
                resolve_asset(pet)


class ScenarioEdgeTests(unittest.TestCase):
    def test_scenario_schema_bounds(self) -> None:
        invalid_scenarios = [
            {},
            {"events": []},
            {"events": ["bad"]},
            {"events": [{"state": "idle", "direction": "000"}]},
            {"events": [{"state": "unknown"}]},
            {"events": [{"state": "idle", "loops": 0}]},
            {"events": [{"direction": "000", "hold_ms": 20}]},
            {"events": [{"state": "idle", "frame_ms": 10}]},
        ]
        for scenario in invalid_scenarios:
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                validate_scenario(scenario)

    def test_load_and_render_preconditions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            list_root = root / "list.json"
            list_root.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_scenario(list_root)

            pet = make_pet(root / "pet")
            scenario = {"events": [{"state": "idle"}]}
            with self.assertRaises(ValueError):
                scenario_frames(pet, scenario, scale=5)

            bad_background = {
                "background": 42,
                "events": [{"state": "idle"}],
            }
            with self.assertRaises(ValueError):
                scenario_frames(pet, bad_background)

    def test_expanded_scenario_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet")
            scenario = {
                "events": [
                    {"state": "failed", "loops": 20}
                    for _index in range(7)
                ]
            }
            with self.assertRaises(ValueError):
                scenario_frames(pet, scenario)


class ProvenanceAndInstallEdgeTests(unittest.TestCase):
    def test_bad_provenance_schema_and_entry_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "artwork/references/sources.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"schema_version": 2}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_provenance(manifest)

            manifest.write_text(
                '{"schema_version":1,"sources":["bad"]}\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                verify_provenance(manifest)

    def test_empty_install_state_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex"
            report = uninstall_pet(codex_home=codex_home)
            self.assertTrue(report["ok"])
            self.assertFalse(report["changed"])
            self.assertEqual(list_backups(codex_home), [])
            with self.assertRaises(FileNotFoundError):
                rollback_pet(codex_home=codex_home)

    def test_filesystem_root_is_not_a_codex_home(self) -> None:
        root = Path(Path.cwd().anchor)
        with self.assertRaises(ValueError):
            resolve_codex_home(root)

    def test_web_dimensions_are_known(self) -> None:
        self.assertEqual(infer_target(TARGETS["web"].dimensions), TARGETS["web"])


if __name__ == "__main__":
    unittest.main()
