from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scales_pet.build import (
    build_release,
    compile_web_atlas,
    sha256_file,
    web_pixels_match_desktop,
)
from scales_pet.validation import validate_source

from .helpers import make_pet, populate_release_text_files


class BuildTests(unittest.TestCase):
    def test_web_compiler_emits_valid_pixel_matching_v1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pet = make_pet(root / "pet")
            web = root / "web-pet" / "scales-web-upload.webp"
            report = compile_web_atlas(pet, web)

            self.assertTrue(report.ok, report.to_dict())
            self.assertTrue(web_pixels_match_desktop(pet, web))
            self.assertTrue(validate_source(web, target_name="web", strict=True).ok)

    def test_release_archives_are_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            make_pet(root / "pet")
            compile_web_atlas(root / "pet", root / "web-pet/scales-web-upload.webp")
            populate_release_text_files(root)
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            build_release(
                root,
                version="0.1.0",
                output=first,
                manifest_output=Path(directory) / "first.json",
                checksums_output=Path(directory) / "first.sha256",
            )
            build_release(
                root,
                version="0.1.0",
                output=second,
                manifest_output=Path(directory) / "second.json",
                checksums_output=Path(directory) / "second.sha256",
            )

            self.assertEqual(sha256_file(first), sha256_file(second))
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                timestamps = {item.date_time for item in archive.infolist()}

        self.assertIn(
            "scales-codex-pet-v0.1.0/release-manifest.json",
            names,
        )
        self.assertEqual(timestamps, {(2020, 1, 1, 0, 0, 0)})

    def test_web_compiler_refuses_to_overwrite_desktop_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pet = make_pet(Path(directory) / "pet")
            source = pet / "spritesheet.webp"
            original_hash = sha256_file(source)

            with self.assertRaises(ValueError):
                compile_web_atlas(pet, source)

            self.assertEqual(sha256_file(source), original_hash)

    def test_release_outputs_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            make_pet(root / "pet")
            compile_web_atlas(root / "pet", root / "web-pet/scales-web-upload.webp")
            populate_release_text_files(root)
            collision = Path(directory) / "release.out"

            with self.assertRaises(ValueError):
                build_release(
                    root,
                    version="0.1.0",
                    output=collision,
                    manifest_output=collision,
                    checksums_output=Path(directory) / "checksums.txt",
                )


if __name__ == "__main__":
    unittest.main()
