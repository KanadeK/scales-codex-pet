from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scales_pet.build import compile_web_atlas
from scripts.build_site import build_site

from .helpers import make_pet


class SiteBuildTests(unittest.TestCase):
    def test_site_build_copies_validated_real_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            make_pet(root / "pet")
            compile_web_atlas(root / "pet", root / "web-pet/scales-web-upload.webp")
            (root / "site").mkdir()
            for name in ("index.html", "style.css", "app.js"):
                (root / "site" / name).write_text(name, encoding="utf-8")
            scenario = root / "examples/scales-quest.json"
            scenario.parent.mkdir(parents=True)
            scenario.write_text(
                '{"schema_version":1,"events":[{"state":"idle"}]}\n',
                encoding="utf-8",
            )
            reference = root / "artwork/references/sintel-scales-film-still.jpg"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"reference")
            (reference.parent / "sources.json").write_text(
                '{"schema_version":1,"sources":[]}\n',
                encoding="utf-8",
            )

            result = build_site(root, root / "build/site")

            self.assertTrue(result["ok"])
            self.assertTrue((root / "build/site/site-data.json").is_file())
            self.assertTrue((root / "build/site/assets/spritesheet.webp").is_file())


if __name__ == "__main__":
    unittest.main()
