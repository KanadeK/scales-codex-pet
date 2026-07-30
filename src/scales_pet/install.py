from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .build import sha256_file
from .model import resolve_asset
from .validation import validate_source

PET_ID = "scales-sintel"
LOCK_MAX_AGE_SECONDS = 15 * 60


def resolve_codex_home(value: str | Path | None = None) -> Path:
    configured = os.environ.get("CODEX_HOME")
    candidate = (
        Path(value).expanduser().resolve()
        if value is not None
        else (
            Path(configured).expanduser().resolve()
            if configured
            else (Path.home() / ".codex").resolve()
        )
    )
    if candidate == Path(candidate.anchor):
        raise ValueError("Codex home must not be a filesystem root")
    if candidate.exists() and not candidate.is_dir():
        raise ValueError(f"Codex home exists but is not a directory: {candidate}")
    return candidate


def _paths(codex_home: Path) -> tuple[Path, Path, Path]:
    pets = codex_home / "pets"
    destination = pets / PET_ID
    backups = codex_home / "pet-backups" / PET_ID
    return pets, destination, backups


@contextlib.contextmanager
def _pet_lock(pets_dir: Path) -> Iterator[Path]:
    pets_dir.mkdir(parents=True, exist_ok=True)
    lock_path = pets_dir / f".{PET_ID}.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(
            f"install lock exists: {lock_path}; run doctor before removing a stale lock"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "pid": os.getpid(),
                "created_at": dt.datetime.now(dt.UTC).isoformat(),
            },
            handle,
        )
        handle.write("\n")
    try:
        yield lock_path
    finally:
        lock_path.unlink(missing_ok=True)


def _backup_name(source_hash: str) -> str:
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{source_hash[:12]}"


def _validate_install_source(source: str | Path) -> Path:
    report = validate_source(source, target_name="desktop", strict=True)
    if not report.ok:
        raise ValueError(f"pet source failed strict validation: {report.to_dict()}")
    asset = resolve_asset(source)
    if not asset.source.is_dir() or asset.manifest_path is None:
        raise ValueError("installation source must be a complete pet directory")
    return asset.source


def install_pet(
    source: str | Path,
    *,
    codex_home: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_dir = _validate_install_source(source)
    home = resolve_codex_home(codex_home)
    pets, destination, backups = _paths(home)
    source_asset = resolve_asset(source_dir)
    source_hash = sha256_file(source_asset.image_path)
    planned_backup = (
        backups / _backup_name(sha256_file(destination / "spritesheet.webp"))
        if destination.exists()
        else None
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "source": str(source_dir),
            "destination": str(destination),
            "would_backup": str(planned_backup) if planned_backup else None,
            "spritesheet_sha256": source_hash,
        }

    staging = pets / f".{PET_ID}.staging-{os.getpid()}-{uuid.uuid4().hex}"
    backup: Path | None = None
    with _pet_lock(pets):
        try:
            shutil.copytree(source_dir, staging, copy_function=shutil.copy2)
            staged_report = validate_source(staging, target_name="desktop", strict=True)
            if not staged_report.ok:
                raise RuntimeError(f"staged package failed validation: {staged_report.to_dict()}")
            if destination.exists():
                backups.mkdir(parents=True, exist_ok=True)
                backup = backups / _backup_name(sha256_file(destination / "spritesheet.webp"))
                os.replace(destination, backup)
            os.replace(staging, destination)
        except Exception:
            if backup is not None and backup.exists() and not destination.exists():
                os.replace(backup, destination)
            if staging.exists():
                shutil.rmtree(staging)
            raise

    return {
        "ok": True,
        "dry_run": False,
        "source": str(source_dir),
        "destination": str(destination),
        "backup": str(backup) if backup else None,
        "spritesheet_sha256": source_hash,
    }


def uninstall_pet(
    *,
    codex_home: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    home = resolve_codex_home(codex_home)
    pets, destination, backups = _paths(home)
    if not destination.exists():
        return {
            "ok": True,
            "dry_run": dry_run,
            "changed": False,
            "destination": str(destination),
            "message": "pet is not installed",
        }
    current_hash = sha256_file(destination / "spritesheet.webp")
    backup = backups / _backup_name(current_hash)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "changed": True,
            "destination": str(destination),
            "would_move_to": str(backup),
        }
    with _pet_lock(pets):
        backups.mkdir(parents=True, exist_ok=True)
        os.replace(destination, backup)
    return {
        "ok": True,
        "dry_run": False,
        "changed": True,
        "destination": str(destination),
        "backup": str(backup),
    }


def list_backups(codex_home: str | Path | None = None) -> list[Path]:
    home = resolve_codex_home(codex_home)
    _pets, _destination, backups = _paths(home)
    if not backups.is_dir():
        return []
    return sorted(
        (path for path in backups.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )


def rollback_pet(
    *,
    codex_home: str | Path | None = None,
    backup: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    home = resolve_codex_home(codex_home)
    pets, destination, backups_root = _paths(home)
    candidates = list_backups(home)
    selected = (
        Path(backup).expanduser().resolve()
        if backup
        else (candidates[0] if candidates else None)
    )
    if selected is None or not selected.is_dir() or backups_root not in selected.parents:
        raise FileNotFoundError("no valid Scales backup is available for rollback")
    report = validate_source(selected, target_name="desktop", strict=True)
    if not report.ok:
        raise ValueError(f"selected backup is invalid: {report.to_dict()}")
    current_backup: Path | None = None
    if destination.exists():
        current_backup = backups_root / _backup_name(
            sha256_file(destination / "spritesheet.webp")
        )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "selected_backup": str(selected),
            "destination": str(destination),
            "would_backup_current": str(current_backup) if current_backup else None,
        }
    with _pet_lock(pets):
        try:
            if destination.exists() and current_backup is not None:
                backups_root.mkdir(parents=True, exist_ok=True)
                os.replace(destination, current_backup)
            os.replace(selected, destination)
        except Exception:
            if current_backup is not None and current_backup.exists() and not destination.exists():
                os.replace(current_backup, destination)
            raise
    return {
        "ok": True,
        "dry_run": False,
        "selected_backup": str(selected),
        "destination": str(destination),
        "previous_current_backup": str(current_backup) if current_backup else None,
    }


def doctor(
    source: str | Path,
    *,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    home = resolve_codex_home(codex_home)
    pets, destination, _backups = _paths(home)
    try:
        source_report = validate_source(source, target_name="desktop", strict=True).to_dict()
        source_asset = resolve_asset(source)
        source_hash = sha256_file(source_asset.image_path)
    except (OSError, RuntimeError, ValueError) as error:
        source_report = {
            "ok": False,
            "errors": [
                {
                    "severity": "error",
                    "code": "source-unreadable",
                    "message": str(error),
                    "repair": "Restore the repository pet from a verified release.",
                }
            ],
            "warnings": [],
        }
        source_hash = None
    if destination.is_dir():
        try:
            installed_report = validate_source(
                destination, target_name="desktop", strict=True
            ).to_dict()
            installed_hash = sha256_file(destination / "spritesheet.webp")
        except (OSError, RuntimeError, ValueError) as error:
            installed_report = {
                "ok": False,
                "errors": [
                    {
                        "severity": "error",
                        "code": "installed-unreadable",
                        "message": str(error),
                        "repair": (
                            "Reinstall from the verified source; "
                            "the damaged copy is backed up."
                        ),
                    }
                ],
                "warnings": [],
            }
            installed_hash = None
    else:
        installed_report = None
        installed_hash = None
    lock = pets / f".{PET_ID}.lock"
    lock_age = (
        max(0.0, dt.datetime.now().timestamp() - lock.stat().st_mtime)
        if lock.exists()
        else None
    )
    repairs: list[str] = []
    if not source_report["ok"]:
        repairs.append("Restore the repository pet and rerun strict validation.")
    if not destination.exists():
        repairs.append("Run scales-pet install --source pet after validating the source.")
    elif installed_report is not None and not installed_report["ok"]:
        repairs.append("Run install again; the current copy will be preserved as a backup.")
    elif installed_hash != source_hash:
        repairs.append("Reinstall from the verified source to replace the drifted copy safely.")
    if lock_age is not None:
        if lock_age > LOCK_MAX_AGE_SECONDS:
            repairs.append(
                f"Inspect and remove stale lock {lock} only after confirming no install is running."
            )
        else:
            repairs.append("Wait for the active install lock to clear before retrying.")
    return {
        "ok": source_report["ok"]
        and bool(installed_report and installed_report["ok"])
        and installed_hash == source_hash
        and lock_age is None,
        "codex_home": str(home),
        "source_validation": source_report,
        "installed_validation": installed_report,
        "source_sha256": source_hash,
        "installed_sha256": installed_hash,
        "hashes_match": installed_hash == source_hash,
        "lock": str(lock) if lock.exists() else None,
        "lock_age_seconds": lock_age,
        "backups": [str(path) for path in list_backups(home)],
        "repairs": repairs,
    }
