from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.release_check import git_report


class ReleaseCheckTests(unittest.TestCase):
    def test_documented_script_entrypoint_loads_from_repository_root(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "scripts/release_check.py", "--help"],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("release gate", completed.stdout)

    def test_strict_git_report_accepts_checkout_and_git_remote_forms(self) -> None:
        for remote_url in (
            "https://github.com/KanadeK/scales-codex-pet",
            "https://github.com/KanadeK/scales-codex-pet.git",
            "git@github.com:KanadeK/scales-codex-pet.git",
        ):
            with self.subTest(remote_url=remote_url):
                observed_environments: list[dict[str, str]] = []

                def fake_run(
                    command: list[str],
                    current_remote: str = remote_url,
                    env: dict[str, str] | None = None,
                    current_environments: list[dict[str, str]] = observed_environments,
                    **_: object,
                ) -> dict[str, object]:
                    self.assertIsNotNone(env)
                    current_environments.append(env or {})
                    if command[:2] == ["git", "status"]:
                        stdout = ""
                    elif command[:2] == ["git", "shortlog"]:
                        stdout = "1\tKanadeK <121669563+KanadeK@users.noreply.github.com>\n"
                    elif command[:2] == ["git", "log"]:
                        stdout = (
                            "abc\tKanadeK\t121669563+KanadeK@users.noreply.github.com"
                            "\tKanadeK\t121669563+KanadeK@users.noreply.github.com"
                            "\tRelease\n"
                        )
                    else:
                        self.assertEqual(command, ["git", "remote", "get-url", "origin"])
                        stdout = current_remote + "\n"
                    return {
                        "ok": True,
                        "command": command,
                        "exit_code": 0,
                        "stdout": stdout,
                        "stderr": "",
                    }

                with patch("scripts.release_check.run_process", side_effect=fake_run):
                    report = git_report(Path("."), strict=True)

                self.assertTrue(report["ok"], report)
                self.assertTrue(report["remote_ok"], report)
                self.assertEqual(len(observed_environments), 4)
                for environment in observed_environments:
                    count = int(environment["GIT_CONFIG_COUNT"])
                    self.assertEqual(environment[f"GIT_CONFIG_KEY_{count - 1}"], "safe.directory")
                    self.assertEqual(
                        environment[f"GIT_CONFIG_VALUE_{count - 1}"],
                        str(Path(".").resolve()),
                    )


if __name__ == "__main__":
    unittest.main()
