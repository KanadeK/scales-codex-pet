from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from scales_pet.model import TARGETS, cell_box, required_cells


def make_pet(
    root: Path,
    *,
    missing: tuple[int, int] | None = None,
    populate_unused: tuple[int, int] | None = None,
    edge: tuple[int, int] | None = None,
    color: tuple[int, int, int, int] = (154, 105, 72, 255),
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = TARGETS["desktop"]
    atlas = Image.new("RGBA", target.dimensions, (0, 0, 0, 0))
    draw = ImageDraw.Draw(atlas)
    for column, row in required_cells(target):
        if (column, row) == missing:
            continue
        left, top, right, bottom = cell_box(column, row)
        margin = 0 if (column, row) == edge else 24
        frame_color = (
            (color[0] + column * 7 + row * 3) % 220 + 20,
            (color[1] + column * 5 + row * 7) % 180 + 20,
            (color[2] + column * 3 + row * 5) % 160 + 20,
            color[3],
        )
        draw.rounded_rectangle(
            (left + margin, top + margin, right - margin - 1, bottom - margin - 1),
            radius=10,
            fill=frame_color,
        )
    if populate_unused is not None:
        left, top, _right, _bottom = cell_box(*populate_unused)
        draw.rectangle((left + 40, top + 40, left + 80, top + 80), fill=color)
    atlas.save(
        root / "spritesheet.webp",
        "WEBP",
        lossless=True,
        quality=100,
        method=6,
        exact=True,
    )
    manifest = {
        "id": "scales-sintel",
        "displayName": "Scales | Sintel",
        "description": "Synthetic test pet.",
        "spriteVersionNumber": 2,
        "spritesheetPath": "spritesheet.webp",
    }
    (root / "pet.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def populate_release_text_files(root: Path) -> None:
    for relative in (
        "README.md",
        "README.zh-CN.md",
        "ASSET_LICENSE.md",
        "NOTICE.md",
        "LICENSE",
        "LICENSES/CC-BY-3.0.txt",
        "CHANGELOG.md",
        "docs/REPAIR.md",
        "scripts/install.sh",
        "scripts/install.ps1",
        "pyproject.toml",
        "src/scales_pet/__init__.py",
        "src/scales_pet/__main__.py",
        "src/scales_pet/build.py",
        "src/scales_pet/cli.py",
        "src/scales_pet/install.py",
        "src/scales_pet/model.py",
        "src/scales_pet/provenance.py",
        "src/scales_pet/scenario.py",
        "src/scales_pet/validation.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {relative}\n", encoding="utf-8")
    provenance = root / "artwork/references/sources.json"
    provenance.parent.mkdir(parents=True, exist_ok=True)
    reference = provenance.parent / "source-reference.bin"
    reference_bytes = b"pinned provenance fixture\n"
    reference.write_bytes(reference_bytes)
    provenance.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "attribution": "Test fixture only.",
                "sources": [
                    {
                        "path": "artwork/references/source-reference.bin",
                        "sha256": hashlib.sha256(reference_bytes).hexdigest(),
                        "page_url": "https://example.com/source-reference",
                        "license": "CC-BY-3.0",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    scenario = root / "examples/scales-quest.json"
    scenario.parent.mkdir(parents=True, exist_ok=True)
    scenario.write_text('{"schema_version": 1, "events": []}\n', encoding="utf-8")
