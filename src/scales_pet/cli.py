from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .build import build_release, compile_web_atlas
from .install import doctor, install_pet, rollback_pet, uninstall_pet
from .provenance import verify_provenance
from .scenario import render_scenario
from .validation import validate_source


def _emit(payload: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
        return
    status = "PASS" if payload.get("ok") else "FAIL"
    print(f"{status}: {payload.get('message', payload.get('target', 'scales-pet'))}")
    for key, value in payload.items():
        if key not in {"ok", "message", "errors", "warnings"} and value is not None:
            print(f"{key}: {value}")
    for group in ("errors", "warnings"):
        for issue in payload.get(group, []):
            print(
                f"{issue['severity'].upper()} {issue['code']}: {issue['message']} "
                f"Repair: {issue['repair']}"
            )


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scales-pet",
        description="Build, validate, replay, install, and package the Scales Codex pet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a desktop or web atlas")
    validate.add_argument("source", nargs="?", default="pet")
    validate.add_argument("--target", choices=("auto", "desktop", "web"), default="auto")
    validate.add_argument("--strict", action="store_true")
    _add_json_flag(validate)

    build_web = subparsers.add_parser(
        "build-web", help="compile desktop v2 rows 0-8 into the web upload format"
    )
    build_web.add_argument("--source", default="pet")
    build_web.add_argument("--output", default="web-pet/scales-web-upload.webp")
    build_web.add_argument("--allow-warnings", action="store_true")
    _add_json_flag(build_web)

    replay = subparsers.add_parser(
        "replay", help="render a lifecycle scenario through the real spritesheet"
    )
    replay.add_argument("scenario", nargs="?", default="examples/scales-quest.json")
    replay.add_argument("--source", default="pet")
    replay.add_argument("--output", default="tmp/scales-quest.gif")
    replay.add_argument("--scale", type=int, choices=(1, 2, 3, 4), default=1)
    _add_json_flag(replay)

    install = subparsers.add_parser("install", help="transactionally install the local v2 pet")
    install.add_argument("--source", default="pet")
    install.add_argument("--codex-home")
    install.add_argument("--dry-run", action="store_true")
    _add_json_flag(install)

    uninstall = subparsers.add_parser(
        "uninstall", help="move an installed pet into the recoverable backup store"
    )
    uninstall.add_argument("--codex-home")
    uninstall.add_argument("--dry-run", action="store_true")
    _add_json_flag(uninstall)

    rollback = subparsers.add_parser("rollback", help="restore a verified pet backup")
    rollback.add_argument("--codex-home")
    rollback.add_argument("--backup")
    rollback.add_argument("--dry-run", action="store_true")
    _add_json_flag(rollback)

    diagnose = subparsers.add_parser(
        "doctor", help="diagnose source, installed copy, lock, hashes, and backups"
    )
    diagnose.add_argument("--source", default="pet")
    diagnose.add_argument("--codex-home")
    _add_json_flag(diagnose)

    provenance = subparsers.add_parser(
        "verify-provenance", help="verify every attributed upstream reference by SHA-256"
    )
    provenance.add_argument(
        "manifest", nargs="?", default="artwork/references/sources.json"
    )
    _add_json_flag(provenance)

    package = subparsers.add_parser(
        "package", help="build a byte-reproducible dual-target release archive"
    )
    package.add_argument("--repo-root", default=".")
    package.add_argument("--version", required=True)
    package.add_argument("--output", required=True)
    package.add_argument("--manifest", required=True)
    package.add_argument("--checksums", required=True)
    _add_json_flag(package)
    return parser


def _run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    command = args.command
    if command == "validate":
        report = validate_source(
            args.source,
            target_name=args.target,
            strict=args.strict,
        )
        return report.to_dict(), 0 if report.ok else 1
    if command == "build-web":
        report = compile_web_atlas(
            args.source,
            args.output,
            strict=not args.allow_warnings,
        )
        payload = report.to_dict()
        payload["output"] = str(Path(args.output).expanduser().resolve())
        return payload, 0
    if command == "replay":
        return (
            render_scenario(
                args.source,
                args.scenario,
                args.output,
                scale=args.scale,
            ),
            0,
        )
    if command == "install":
        return (
            install_pet(
                args.source,
                codex_home=args.codex_home,
                dry_run=args.dry_run,
            ),
            0,
        )
    if command == "uninstall":
        return (
            uninstall_pet(codex_home=args.codex_home, dry_run=args.dry_run),
            0,
        )
    if command == "rollback":
        return (
            rollback_pet(
                codex_home=args.codex_home,
                backup=args.backup,
                dry_run=args.dry_run,
            ),
            0,
        )
    if command == "doctor":
        payload = doctor(args.source, codex_home=args.codex_home)
        return payload, 0 if payload["ok"] else 1
    if command == "verify-provenance":
        payload = verify_provenance(args.manifest)
        return payload, 0 if payload["ok"] else 1
    if command == "package":
        return (
            build_release(
                args.repo_root,
                version=args.version,
                output=args.output,
                manifest_output=args.manifest,
                checksums_output=args.checksums,
            ),
            0,
        )
    raise AssertionError(f"unhandled command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload, exit_code = _run(args)
    except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as error:
        payload = {
            "ok": False,
            "error": type(error).__name__,
            "message": str(error),
            "repair": "Run `scales-pet doctor --json` or follow docs/REPAIR.md.",
        }
        _emit(payload, json_mode=bool(getattr(args, "json", False)))
        return 2
    _emit(payload, json_mode=bool(getattr(args, "json", False)))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
