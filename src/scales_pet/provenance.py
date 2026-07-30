from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .build import sha256_file


def verify_provenance(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("sources")
    if payload.get("schema_version") != 1 or not isinstance(entries, list) or not entries:
        raise ValueError("provenance manifest must use schema_version 1 and list sources")

    root = path.parents[2]
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"source entry {index} must be an object")
        relative = entry.get("path")
        expected = entry.get("sha256")
        page_url = entry.get("page_url")
        license_id = entry.get("license")
        if (
            not isinstance(relative, str)
            or not relative
            or not isinstance(expected, str)
            or not expected
            or not isinstance(page_url, str)
            or not page_url
        ):
            raise ValueError(f"source entry {index} is missing path, sha256, or page_url")
        source = (root / relative).resolve()
        if root not in source.parents:
            raise ValueError(f"source entry {index} escapes the repository")
        actual = sha256_file(source) if source.is_file() else None
        record = {
            "path": relative,
            "exists": source.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "license": license_id,
            "page_url": page_url,
            "ok": actual == expected,
        }
        results.append(record)
        if not source.is_file():
            errors.append(
                {
                    "code": "source-missing",
                    "path": str(relative),
                    "repair": "Restore the exact attributed source file and verify its SHA-256.",
                }
            )
        elif actual != expected:
            errors.append(
                {
                    "code": "source-hash",
                    "path": str(relative),
                    "repair": (
                        "Do not update the hash blindly; "
                        "restore or re-audit the reference file."
                    ),
                }
            )
        if license_id != "CC-BY-3.0":
            errors.append(
                {
                    "code": "license-id",
                    "path": str(relative),
                    "repair": (
                        "Record the exact upstream license identifier "
                        "and review compatibility."
                    ),
                }
            )
        if not str(page_url).startswith("https://"):
            errors.append(
                {
                    "code": "source-url",
                    "path": str(relative),
                    "repair": "Use the canonical HTTPS file-description page.",
                }
            )
    return {
        "ok": not errors,
        "manifest": str(path),
        "attribution": payload.get("attribution"),
        "sources": results,
        "errors": errors,
    }
