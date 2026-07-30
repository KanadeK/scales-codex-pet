from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scales_pet.cli import main


class StubReport:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "target": "desktop",
            "errors": [] if self.ok else [
                {
                    "severity": "error",
                    "code": "fixture",
                    "message": "fixture failure",
                    "repair": "repair fixture",
                }
            ],
            "warnings": [],
        }


class CliTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(arguments)
        return exit_code, json.loads(output.getvalue())

    def test_validate_and_build_web_dispatch(self) -> None:
        with patch("scales_pet.cli.validate_source", return_value=StubReport()) as validate:
            exit_code, payload = self.invoke(
                ["validate", "pet", "--target", "desktop", "--strict", "--json"]
            )
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        validate.assert_called_once_with("pet", target_name="desktop", strict=True)

        with patch("scales_pet.cli.compile_web_atlas", return_value=StubReport()) as compile_web:
            exit_code, payload = self.invoke(
                [
                    "build-web",
                    "--source",
                    "pet",
                    "--output",
                    "web.webp",
                    "--allow-warnings",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        compile_web.assert_called_once_with("pet", "web.webp", strict=False)

    def test_replay_install_uninstall_and_rollback_dispatch(self) -> None:
        successful = {"ok": True}
        with patch("scales_pet.cli.render_scenario", return_value=successful) as render:
            exit_code, _payload = self.invoke(
                [
                    "replay",
                    "scenario.json",
                    "--source",
                    "pet",
                    "--output",
                    "out.gif",
                    "--scale",
                    "2",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 0)
        render.assert_called_once_with("pet", "scenario.json", "out.gif", scale=2)

        with patch("scales_pet.cli.install_pet", return_value=successful) as install:
            exit_code, _payload = self.invoke(
                [
                    "install",
                    "--source",
                    "pet",
                    "--codex-home",
                    "home",
                    "--dry-run",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 0)
        install.assert_called_once_with("pet", codex_home="home", dry_run=True)

        with patch("scales_pet.cli.uninstall_pet", return_value=successful) as uninstall:
            exit_code, _payload = self.invoke(
                ["uninstall", "--codex-home", "home", "--dry-run", "--json"]
            )
        self.assertEqual(exit_code, 0)
        uninstall.assert_called_once_with(codex_home="home", dry_run=True)

        with patch("scales_pet.cli.rollback_pet", return_value=successful) as rollback:
            exit_code, _payload = self.invoke(
                [
                    "rollback",
                    "--codex-home",
                    "home",
                    "--backup",
                    "backup",
                    "--dry-run",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 0)
        rollback.assert_called_once_with(
            codex_home="home",
            backup="backup",
            dry_run=True,
        )

    def test_doctor_provenance_and_package_dispatch(self) -> None:
        with patch("scales_pet.cli.doctor", return_value={"ok": False}) as doctor:
            exit_code, payload = self.invoke(
                ["doctor", "--source", "pet", "--codex-home", "home", "--json"]
            )
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        doctor.assert_called_once_with("pet", codex_home="home")

        with patch(
            "scales_pet.cli.verify_provenance",
            return_value={"ok": True},
        ) as verify:
            exit_code, _payload = self.invoke(
                ["verify-provenance", "sources.json", "--json"]
            )
        self.assertEqual(exit_code, 0)
        verify.assert_called_once_with("sources.json")

        with patch("scales_pet.cli.build_release", return_value={"ok": True}) as package:
            exit_code, _payload = self.invoke(
                [
                    "package",
                    "--repo-root",
                    ".",
                    "--version",
                    "0.1.0",
                    "--output",
                    "release.zip",
                    "--manifest",
                    "manifest.json",
                    "--checksums",
                    "SHA256SUMS.txt",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 0)
        package.assert_called_once_with(
            ".",
            version="0.1.0",
            output="release.zip",
            manifest_output="manifest.json",
            checksums_output="SHA256SUMS.txt",
        )

    def test_errors_become_json_with_repair_and_text_mode_prints_issues(self) -> None:
        with patch("scales_pet.cli.validate_source", side_effect=ValueError("bad atlas")):
            exit_code, payload = self.invoke(["validate", "bad.webp", "--json"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["error"], "ValueError")
        self.assertIn("doctor", str(payload["repair"]))

        output = io.StringIO()
        with (
            patch("scales_pet.cli.validate_source", return_value=StubReport(False)),
            redirect_stdout(output),
        ):
            exit_code = main(["validate", "bad.webp"])
        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR fixture", output.getvalue())

    def test_build_web_reports_resolved_output_path(self) -> None:
        with patch("scales_pet.cli.compile_web_atlas", return_value=StubReport()):
            exit_code, payload = self.invoke(
                ["build-web", "--output", "relative.webp", "--json"]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(Path(str(payload["output"])).name, "relative.webp")


if __name__ == "__main__":
    unittest.main()
