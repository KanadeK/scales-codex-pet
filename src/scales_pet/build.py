from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .model import TARGETS, resolve_asset
from .validation import ValidationReport, validate_source

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def compile_web_atlas(
    source: str | Path,
    output: str | Path,
    *,
    strict: bool = True,
) -> ValidationReport:
    desktop_report = validate_source(source, target_name="desktop", strict=strict)
    if not desktop_report.ok:
        raise ValueError(f"desktop atlas failed validation: {desktop_report.to_dict()}")

    asset = resolve_asset(source)
    destination = Path(output).expanduser().resolve()
    if destination == asset.image_path:
        raise ValueError("web output must not overwrite the authoritative desktop atlas")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(asset.image_path) as opened:
        opened.load()
        web = opened.convert("RGBA").crop((0, 0, *TARGETS["web"].dimensions))
        with tempfile.NamedTemporaryFile(
            suffix=".webp", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        try:
            web.save(
                temporary,
                "WEBP",
                lossless=True,
                quality=100,
                method=6,
                exact=True,
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    web_report = validate_source(destination, target_name="web", strict=strict)
    if not web_report.ok:
        destination.unlink(missing_ok=True)
        raise ValueError(f"compiled web atlas failed validation: {web_report.to_dict()}")
    return web_report


def web_pixels_match_desktop(desktop: str | Path, web: str | Path) -> bool:
    desktop_asset = resolve_asset(desktop)
    web_asset = resolve_asset(web)
    with (
        Image.open(desktop_asset.image_path) as desktop_image,
        Image.open(web_asset.image_path) as web_image,
    ):
        desktop_crop = desktop_image.convert("RGBA").crop((0, 0, *TARGETS["web"].dimensions))
        return desktop_crop.tobytes() == web_image.convert("RGBA").tobytes()


@dataclass(frozen=True, slots=True)
class ReleaseFile:
    source: Path
    archive_path: str
    executable: bool = False


def _zip_info(name: str, *, executable: bool) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    permissions = 0o755 if executable else 0o644
    info.external_attr = (permissions & 0xFFFF) << 16
    return info


def _default_release_files(repo_root: Path) -> list[ReleaseFile]:
    entries: list[tuple[str, bool]] = [
        ("pet/pet.json", False),
        ("pet/spritesheet.webp", False),
        ("web-pet/scales-web-upload.webp", False),
        ("artwork/references/sources.json", False),
        ("examples/scales-quest.json", False),
        ("pyproject.toml", False),
        ("src/scales_pet/__init__.py", False),
        ("src/scales_pet/__main__.py", False),
        ("src/scales_pet/build.py", False),
        ("src/scales_pet/cli.py", False),
        ("src/scales_pet/install.py", False),
        ("src/scales_pet/model.py", False),
        ("src/scales_pet/provenance.py", False),
        ("src/scales_pet/scenario.py", False),
        ("src/scales_pet/validation.py", False),
        ("README.md", False),
        ("README.zh-CN.md", False),
        ("ASSET_LICENSE.md", False),
        ("NOTICE.md", False),
        ("LICENSE", False),
        ("LICENSES/CC-BY-3.0.txt", False),
        ("CHANGELOG.md", False),
        ("docs/REPAIR.md", False),
        ("scripts/install.sh", True),
        ("scripts/install.ps1", False),
    ]
    files = [
        ReleaseFile(repo_root / relative, relative.replace("\\", "/"), executable)
        for relative, executable in entries
    ]
    missing = [str(item.source) for item in files if not item.source.is_file()]
    if missing:
        raise FileNotFoundError(f"release inputs are missing: {missing}")
    return files


def _manifest_for_files(version: str, files: Iterable[ReleaseFile]) -> dict[str, Any]:
    records = [
        {
            "path": item.archive_path,
            "bytes": item.source.stat().st_size,
            "sha256": sha256_file(item.source),
        }
        for item in sorted(files, key=lambda entry: entry.archive_path)
    ]
    return {
        "schema_version": 1,
        "project": "scales-codex-pet",
        "version": version,
        "pet_id": "scales-sintel",
        "targets": {
            "desktop": {"dimensions": [1536, 2288], "spriteVersionNumber": 2},
            "web": {"dimensions": [1536, 1872]},
        },
        "files": records,
    }


def build_release(
    repo_root: str | Path,
    *,
    version: str,
    output: str | Path,
    manifest_output: str | Path,
    checksums_output: str | Path,
) -> dict[str, Any]:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise ValueError("version must be a semantic version without a leading v")

    root = Path(repo_root).expanduser().resolve()
    desktop = root / "pet"
    web = root / "web-pet" / "scales-web-upload.webp"
    for source, target in ((desktop, "desktop"), (web, "web")):
        report = validate_source(source, target_name=target, strict=True)
        if not report.ok:
            raise ValueError(f"{target} release input failed validation: {report.to_dict()}")
    if not web_pixels_match_desktop(desktop, web):
        raise ValueError("web atlas pixels do not exactly match desktop rows 0-8")

    output_path = Path(output).expanduser().resolve()
    manifest_path = Path(manifest_output).expanduser().resolve()
    checksums_path = Path(checksums_output).expanduser().resolve()
    if len({output_path, manifest_path, checksums_path}) != 3:
        raise ValueError("archive, manifest, and checksum outputs must be different files")
    release_files = _default_release_files(root)
    manifest = _manifest_for_files(version, release_files)
    manifest_bytes = _json_bytes(manifest)
    prefix = f"scales-codex-pet-v{version}/"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".zip", dir=output_path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for item in sorted(release_files, key=lambda entry: entry.archive_path):
                info = _zip_info(prefix + item.archive_path, executable=item.executable)
                archive.writestr(info, item.source.read_bytes())
            archive.writestr(
                _zip_info(prefix + "release-manifest.json", executable=False),
                manifest_bytes,
            )
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)

    _atomic_write(manifest_path, manifest_bytes)
    archive_hash = sha256_file(output_path)
    checksum_lines = [
        f"{archive_hash}  {output_path.name}",
        f"{sha256_file(manifest_path)}  {manifest_path.name}",
    ]
    _atomic_write(checksums_path, ("\n".join(checksum_lines) + "\n").encode())
    return {
        "ok": True,
        "version": version,
        "archive": str(output_path),
        "archive_sha256": archive_hash,
        "archive_bytes": output_path.stat().st_size,
        "manifest": str(manifest_path),
        "checksums": str(checksums_path),
        "files": len(release_files) + 1,
    }
