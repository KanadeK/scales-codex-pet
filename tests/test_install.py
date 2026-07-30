from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scales_pet.install import (
    doctor,
    install_pet,
    list_backups,
    rollback_pet,
    uninstall_pet,
)

from .helpers import make_pet


class InstallTests(unittest.TestCase):
    def test_install_reinstall_uninstall_and_rollback_are_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_pet(root / "source")
            codex_home = root / "codex-home"

            dry_run = install_pet(source, codex_home=codex_home, dry_run=True)
            first = install_pet(source, codex_home=codex_home)
            healthy = doctor(source, codex_home=codex_home)
            make_pet(source, color=(170, 90, 60, 255))
            second = install_pet(source, codex_home=codex_home)
            backups_after_reinstall = list_backups(codex_home)
            removed = uninstall_pet(codex_home=codex_home)
            restored = rollback_pet(codex_home=codex_home)

            destination = codex_home / "pets/scales-sintel"
            self.assertTrue(dry_run["dry_run"])
            self.assertIsNone(first["backup"])
            self.assertTrue(healthy["ok"], healthy)
            self.assertIsNotNone(second["backup"])
            self.assertEqual(len(backups_after_reinstall), 1)
            self.assertTrue(removed["changed"])
            self.assertTrue(restored["ok"])
            self.assertTrue(destination.is_dir())

    def test_doctor_reports_corrupt_install_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_pet(root / "source")
            codex_home = root / "codex-home"
            install_pet(source, codex_home=codex_home)
            installed = codex_home / "pets/scales-sintel/spritesheet.webp"
            installed.write_bytes(b"not an image")

            report = doctor(source, codex_home=codex_home)

        self.assertFalse(report["ok"])
        self.assertFalse(report["installed_validation"]["ok"])
        self.assertTrue(report["repairs"])


if __name__ == "__main__":
    unittest.main()
