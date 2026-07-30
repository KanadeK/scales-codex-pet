#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from scales_pet.build import sha256_file, web_pixels_match_desktop
from scales_pet.scenario import load_scenario
from scales_pet.validation import validate_source


def copy_file(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"site input is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "path": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def build_site(repo_root: Path, output: Path) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    destination = output.expanduser().resolve()
    report = validate_source(root / "pet", target_name="desktop", strict=True)
    if not report.ok:
        raise ValueError(f"site requires a valid desktop pet: {report.to_dict()}")
    web_report = validate_source(
        root / "web-pet/scales-web-upload.webp",
        target_name="web",
        strict=True,
    )
    if not web_report.ok:
        raise ValueError(f"site requires a valid web pet: {web_report.to_dict()}")
    if not web_pixels_match_desktop(
        root / "pet",
        root / "web-pet/scales-web-upload.webp",
    ):
        raise ValueError("site web pet does not match the authoritative desktop crop")
    load_scenario(root / "examples/scales-quest.json")

    if destination == root or root not in destination.parents:
        raise ValueError("site output must be a dedicated directory inside the repository")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    sources = {
        root / "site/index.html": destination / "index.html",
        root / "site/style.css": destination / "style.css",
        root / "site/app.js": destination / "app.js",
        root / "pet/spritesheet.webp": destination / "assets/spritesheet.webp",
        root / "web-pet/scales-web-upload.webp": destination / "pet/scales-web-upload.webp",
        root / "examples/scales-quest.json": destination / "assets/scales-quest.json",
        root / "artwork/references/sintel-scales-film-still.jpg":
            destination / "assets/sintel-scales-film-still.jpg",
        root / "artwork/references/sources.json":
            destination / "artwork/references/sources.json",
    }
    files = [copy_file(source, target) for source, target in sources.items()]
    metadata = {
        "schema_version": 1,
        "project": "scales-codex-pet",
        "atlas": {
            "path": "assets/spritesheet.webp",
            "dimensions": [1536, 2288],
            "sha256": sha256_file(root / "pet/spritesheet.webp"),
        },
        "web_pet": {
            "path": "pet/scales-web-upload.webp",
            "dimensions": [1536, 1872],
            "sha256": sha256_file(root / "web-pet/scales-web-upload.webp"),
        },
        "files": sorted(files, key=lambda item: str(item["path"])),
    }
    data_path = destination / "site-data.json"
    data_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "output": str(destination),
        "files": len(files) + 1,
        "atlas_sha256": metadata["atlas"]["sha256"],
        "web_pet_sha256": metadata["web_pet"]["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline Scales project site.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="build/site")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_site(Path(args.repo_root), Path(args.output))
        exit_code = 0
    except (FileNotFoundError, OSError, ValueError) as error:
        payload = {
            "ok": False,
            "error": type(error).__name__,
            "message": str(error),
            "repair": "Validate pet/, compile web-pet/, then run this command again.",
        }
        exit_code = 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(("PASS" if payload["ok"] else "FAIL") + f": {payload}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
