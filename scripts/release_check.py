#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scales_pet.build import (
    FIXED_ZIP_TIME,
    build_release,
    sha256_file,
    web_pixels_match_desktop,
)
from scales_pet.provenance import verify_provenance
from scales_pet.scenario import render_scenario
from scales_pet.validation import validate_source

try:
    from scripts.build_site import build_site
except ModuleNotFoundError:
    from build_site import build_site


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: Any
    repair: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "repair": self.repair,
        }


def run_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def record(
    checks: list[Check],
    name: str,
    repair: str,
    action: Callable[[], Any],
    predicate: Callable[[Any], bool] = bool,
) -> None:
    try:
        detail = action()
        checks.append(Check(name, predicate(detail), detail, repair))
    except Exception as error:
        checks.append(
            Check(
                name,
                False,
                {"error": type(error).__name__, "message": str(error)},
                repair,
            )
        )


def text_files(root: Path) -> list[Path]:
    excluded = {".git", ".mypy_cache", ".ruff_cache", "__pycache__", "build", "dist"}
    suffixes = {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".ps1",
        ".py",
        ".sh",
        ".toml",
        ".txt",
        ".yml",
        ".yaml",
    }
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and not any(part in excluded for part in path.parts)
        and "hatch-run" not in path.parts
    )


def hygiene_report(root: Path) -> dict[str, Any]:
    placeholders: list[str] = []
    secret_like: list[str] = []
    coauthors: list[str] = []
    site_dashes: list[str] = []
    placeholder_terms = ("TO" + "DO", "FIX" + "ME", "X" + "XX", "T" + "BD")
    placeholder_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in placeholder_terms) + r")\b"
    )
    coauthor_marker = "co-" + "authored-by:"
    secret_pattern = re.compile(
        r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})"
    )
    for path in text_files(root):
        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8")
        for number, line in enumerate(content.splitlines(), start=1):
            location = f"{relative}:{number}"
            if placeholder_pattern.search(line):
                placeholders.append(location)
            if secret_pattern.search(line):
                secret_like.append(location)
            if coauthor_marker in line.lower():
                coauthors.append(location)
            if relative.startswith("site/") and ("\u2013" in line or "\u2014" in line):
                site_dashes.append(location)
    return {
        "ok": not placeholders and not secret_like and not coauthors and not site_dashes,
        "placeholders": placeholders,
        "secret_like": secret_like,
        "co_authored_by": coauthors,
        "site_forbidden_dashes": site_dashes,
        "files_scanned": len(text_files(root)),
    }


def deterministic_package_report(root: Path, temporary_root: Path) -> dict[str, Any]:
    outputs: list[Path] = []
    manifests: list[Path] = []
    for name in ("first", "second"):
        archive = temporary_root / f"{name}.zip"
        manifest = temporary_root / f"{name}.json"
        build_release(
            root,
            version="0.1.0",
            output=archive,
            manifest_output=manifest,
            checksums_output=temporary_root / f"{name}.sha256",
        )
        outputs.append(archive)
        manifests.append(manifest)
    with zipfile.ZipFile(outputs[0]) as archive:
        unsafe = [
            name
            for name in archive.namelist()
            if name.startswith("/") or ".." in Path(name).parts
        ]
        timestamps = sorted({item.date_time for item in archive.infolist()})
        names = archive.namelist()
    hashes = [sha256_file(path) for path in outputs]
    manifest_hashes = [sha256_file(path) for path in manifests]
    return {
        "ok": (
            len(set(hashes)) == 1
            and len(set(manifest_hashes)) == 1
            and timestamps == [FIXED_ZIP_TIME]
            and not unsafe
        ),
        "archive_sha256": hashes,
        "manifest_sha256": manifest_hashes,
        "timestamps": timestamps,
        "unsafe_paths": unsafe,
        "entries": len(names),
    }


def git_report(root: Path, strict: bool) -> dict[str, Any]:
    git_env = os.environ.copy()
    try:
        config_index = int(git_env.get("GIT_CONFIG_COUNT", "0"))
    except ValueError:
        config_index = 0
    git_env["GIT_CONFIG_COUNT"] = str(config_index + 1)
    git_env[f"GIT_CONFIG_KEY_{config_index}"] = "safe.directory"
    git_env[f"GIT_CONFIG_VALUE_{config_index}"] = str(root.resolve())

    status = run_process(["git", "status", "--porcelain"], cwd=root, env=git_env)
    shortlog = run_process(["git", "shortlog", "-sne", "HEAD"], cwd=root, env=git_env)
    log = run_process(
        ["git", "log", "--format=%H%x09%an%x09%ae%x09%cn%x09%ce%x09%B"],
        cwd=root,
        env=git_env,
    )
    remote = run_process(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        env=git_env,
    )
    log_text = str(log["stdout"])
    has_coauthor = ("co-" + "authored-by:") in log_text.lower()
    identity_missing = bool(
        log["ok"]
        and any(
            not field.strip()
            for line in log_text.splitlines()
            if "\t" in line
            for field in line.split("\t")[1:5]
        )
    )
    clean = status["ok"] and not str(status["stdout"]).strip()
    history_ok = log["ok"] and shortlog["ok"] and not has_coauthor and not identity_missing
    remote_url = str(remote["stdout"]).strip().rstrip("/")
    normalized_remote = (
        remote_url[:-4] if remote_url.lower().endswith(".git") else remote_url
    )
    canonical_remote = normalized_remote.lower().replace(
        "git@github.com:", "https://github.com/"
    )
    remote_ok = remote["ok"] and canonical_remote.endswith(
        "github.com/kanadek/scales-codex-pet"
    )
    return {
        "ok": history_ok and (not strict or (clean and remote_ok)),
        "strict": strict,
        "clean": clean,
        "remote_ok": remote_ok,
        "remote": str(remote["stdout"]).strip() if remote["ok"] else None,
        "shortlog": str(shortlog["stdout"]).strip(),
        "co_authored_by": has_coauthor,
        "identity_missing": identity_missing,
        "status": str(status["stdout"]).strip().splitlines(),
        "history_available": log["ok"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible local release gate for Scales Codex Pet."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).expanduser().resolve()
    checks: list[Check] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")

    record(
        checks,
        "unit-tests",
        "Run the failing test directly, repair the implementation, then rerun the full suite.",
        lambda: run_process(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-t",
                ".",
                "-v",
            ],
            cwd=root,
            env=env,
        ),
        lambda detail: bool(detail["ok"]),
    )
    record(
        checks,
        "reference-provenance",
        "Restore the pinned reference byte or correct its audited metadata.",
        lambda: verify_provenance(root / "artwork/references/sources.json"),
        lambda detail: bool(detail["ok"]),
    )
    record(
        checks,
        "desktop-atlas",
        "Regenerate the complete failing animation row, reassemble, and validate again.",
        lambda: validate_source(root / "pet", target_name="desktop", strict=True).to_dict(),
        lambda detail: bool(detail["ok"]),
    )
    record(
        checks,
        "web-atlas",
        "Run scales-pet build-web, then rerun strict validation.",
        lambda: validate_source(
            root / "web-pet/scales-web-upload.webp",
            target_name="web",
            strict=True,
        ).to_dict(),
        lambda detail: bool(detail["ok"]),
    )
    record(
        checks,
        "cross-target-pixels",
        "Rebuild the web atlas from the authoritative desktop atlas.",
        lambda: web_pixels_match_desktop(
            root / "pet",
            root / "web-pet/scales-web-upload.webp",
        ),
    )
    record(
        checks,
        "repository-hygiene",
        "Remove placeholders, secret-like values, co-author trailers, and forbidden site dashes.",
        lambda: hygiene_report(root),
        lambda detail: bool(detail["ok"]),
    )

    build_root = root / "build"
    build_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-check-", dir=build_root) as directory:
        temporary_root = Path(directory)
        record(
            checks,
            "scenario-replay",
            "Repair the scenario schema or the referenced animation state and rerender.",
            lambda: render_scenario(
                root / "pet",
                root / "examples/scales-quest.json",
                temporary_root / "scales-quest.gif",
            ),
            lambda detail: bool(detail["ok"]) and int(detail["frames"]) > 0,
        )
        record(
            checks,
            "site-build",
            "Restore the required source file, validate both atlases, and rebuild the site.",
            lambda: build_site(root, temporary_root / "site"),
            lambda detail: bool(detail["ok"]),
        )
        record(
            checks,
            "reproducible-package",
            "Inspect file ordering, timestamps, permissions, and mutable metadata in the ZIP.",
            lambda: deterministic_package_report(root, temporary_root),
            lambda detail: bool(detail["ok"]),
        )

    record(
        checks,
        "git-history",
        "Commit with the configured KanadeK identity, remove co-author trailers, and set origin.",
        lambda: git_report(root, bool(args.strict)),
        lambda detail: bool(detail["ok"]),
    )
    failed = [check.name for check in checks if not check.ok]
    payload = {
        "ok": not failed,
        "strict": bool(args.strict),
        "checks": [check.to_dict() for check in checks],
        "failed": failed,
        "repair": (
            "Apply the repair text for each failed check and rerun the same command."
            if failed
            else None
        ),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(("PASS" if payload["ok"] else "FAIL") + ": release-check")
        for check in checks:
            print(f"{'PASS' if check.ok else 'FAIL'} {check.name}")
            if not check.ok:
                print(f"  Repair: {check.repair}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
