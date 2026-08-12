from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from PIL import Image

from .model import (
    CELL_HEIGHT,
    CELL_WIDTH,
    MAX_FILE_BYTES,
    TARGETS,
    ResolvedAsset,
    TargetSpec,
    cell_box,
    infer_target,
    required_cells,
    resolve_asset,
    unused_cells,
)

Severity = Literal["error", "warning"]
CHROMA_ALPHA_MINIMUM = 16


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    code: str
    message: str
    repair: str
    location: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(slots=True)
class ValidationReport:
    source: str
    image: str
    target: str
    strict: bool
    dimensions: tuple[int, int]
    image_format: str | None
    image_mode: str
    file_bytes: int
    required_cells: int = 0
    populated_required_cells: int = 0
    unused_cells: int = 0
    empty_unused_cells: int = 0
    hidden_rgb_pixels: int = 0
    chroma_pixels: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors and (not self.strict or not self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source": self.source,
            "image": self.image,
            "target": self.target,
            "strict": self.strict,
            "dimensions": list(self.dimensions),
            "format": self.image_format,
            "mode": self.image_mode,
            "file_bytes": self.file_bytes,
            "required_cells": self.required_cells,
            "populated_required_cells": self.populated_required_cells,
            "unused_cells": self.unused_cells,
            "empty_unused_cells": self.empty_unused_cells,
            "hidden_rgb_pixels": self.hidden_rgb_pixels,
            "chroma_pixels": self.chroma_pixels,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def _manifest_issues(asset: ResolvedAsset, target: TargetSpec) -> list[Issue]:
    if target.name != "desktop":
        return []
    if asset.manifest is None:
        return [
            Issue(
                "warning",
                "manifest-not-checked",
                "A raw v2 atlas was validated without pet.json.",
                "Validate the containing pet directory before release.",
            )
        ]

    manifest = asset.manifest
    issues: list[Issue] = []
    if manifest.get("spriteVersionNumber") != 2:
        issues.append(
            Issue(
                "error",
                "sprite-version",
                "pet.json must declare spriteVersionNumber: 2 for an 11-row atlas.",
                "Set spriteVersionNumber to 2 and validate again.",
                "pet.json",
            )
        )
    pet_id = manifest.get("id")
    if not isinstance(pet_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", pet_id):
        issues.append(
            Issue(
                "error",
                "pet-id",
                "pet.json id must be a lowercase kebab-case string.",
                "Use an id such as scales-sintel.",
                "pet.json",
            )
        )
    for field_name in ("displayName", "description"):
        if not isinstance(manifest.get(field_name), str) or not manifest[field_name].strip():
            issues.append(
                Issue(
                    "error",
                    f"manifest-{field_name}",
                    f"pet.json {field_name} must be a non-empty string.",
                    f"Add a meaningful {field_name} value.",
                    "pet.json",
                )
            )
    if manifest.get("spritesheetPath") != asset.image_path.name:
        issues.append(
            Issue(
                "error",
                "spritesheet-path",
                "pet.json spritesheetPath must name the shipped spritesheet file.",
                f'Set spritesheetPath to "{asset.image_path.name}".',
                "pet.json",
            )
        )
    return issues


def _rgba_pixels(image: Image.Image) -> Iterable[tuple[int, int, int, int]]:
    flattened = getattr(image, "get_flattened_data", None)
    pixels = flattened() if callable(flattened) else image.getdata()
    return cast(Iterable[tuple[int, int, int, int]], pixels)


def _count_hidden_rgb(image: Image.Image) -> int:
    return sum(
        1
        for red, green, blue, alpha in _rgba_pixels(image)
        if alpha == 0 and (red or green or blue)
    )


def _count_chroma(image: Image.Image, key: tuple[int, int, int], tolerance: int = 10) -> int:
    limit = tolerance * tolerance
    key_red, key_green, key_blue = key
    return sum(
        1
        for red, green, blue, alpha in _rgba_pixels(image)
        if alpha > CHROMA_ALPHA_MINIMUM
        and (red - key_red) ** 2 + (green - key_green) ** 2 + (blue - key_blue) ** 2
        <= limit
    )


def validate_source(
    source: str | Path,
    *,
    target_name: str = "auto",
    strict: bool = False,
    chroma_key: tuple[int, int, int] = (0, 255, 255),
) -> ValidationReport:
    asset = resolve_asset(source)
    with Image.open(asset.image_path) as opened:
        opened.load()
        dimensions = opened.size
        detected = infer_target(dimensions)
        requested = detected if target_name == "auto" else TARGETS.get(target_name)
        if target_name != "auto" and requested is None:
            raise ValueError(f"unknown target {target_name!r}; expected auto, desktop, or web")
        target = requested or TARGETS["desktop"]
        report = ValidationReport(
            source=str(asset.source),
            image=str(asset.image_path),
            target=detected.name if target_name == "auto" and detected else target.name,
            strict=strict,
            dimensions=dimensions,
            image_format=opened.format,
            image_mode=opened.mode,
            file_bytes=asset.image_path.stat().st_size,
        )

        if detected is None:
            report.issues.append(
                Issue(
                    "error",
                    "dimensions",
                    f"Atlas dimensions {dimensions[0]}x{dimensions[1]} match no supported target.",
                    "Build a 1536x2288 desktop v2 atlas or a 1536x1872 web atlas.",
                    asset.image_path.name,
                )
            )
            return report
        if target_name != "auto" and detected.name != target.name:
            report.issues.append(
                Issue(
                    "error",
                    "target-dimensions",
                    f"Expected {target.dimensions[0]}x{target.dimensions[1]} for {target.name}, "
                    f"found {dimensions[0]}x{dimensions[1]}.",
                    f"Use the {detected.name} target or rebuild for {target.name}.",
                    asset.image_path.name,
                )
            )
            return report

        report.target = detected.name
        target = detected
        report.issues.extend(_manifest_issues(asset, target))

        if opened.format not in {"PNG", "WEBP"}:
            report.issues.append(
                Issue(
                    "error",
                    "image-format",
                    f"Unsupported atlas format {opened.format!r}.",
                    "Save the atlas as transparent PNG or lossless WebP.",
                    asset.image_path.name,
                )
            )
        if "A" not in opened.getbands():
            report.issues.append(
                Issue(
                    "error",
                    "alpha-channel",
                    "Atlas has no alpha channel.",
                    "Export RGBA PNG or lossless WebP with transparency.",
                    asset.image_path.name,
                )
            )
        if report.file_bytes > MAX_FILE_BYTES:
            report.issues.append(
                Issue(
                    "error",
                    "file-size",
                    f"Atlas is {report.file_bytes} bytes; the public limit is {MAX_FILE_BYTES}.",
                    "Use lossless WebP and simplify excess texture detail.",
                    asset.image_path.name,
                )
            )

        rgba = opened.convert("RGBA")
        alpha = rgba.getchannel("A")
        required = required_cells(target)
        unused = unused_cells(target)
        report.required_cells = len(required)
        report.unused_cells = len(unused)

        for column, row in sorted(required, key=lambda item: (item[1], item[0])):
            cell_alpha = alpha.crop(cell_box(column, row))
            bounds = cell_alpha.getbbox()
            location = f"row={row},column={column}"
            if bounds is None:
                report.issues.append(
                    Issue(
                        "error",
                        "required-cell-empty",
                        f"Required cell {location} is empty.",
                        "Regenerate or restore the complete containing animation row.",
                        location,
                    )
                )
                continue
            report.populated_required_cells += 1
            left, top, right, bottom = bounds
            if left == 0 or top == 0 or right == CELL_WIDTH or bottom == CELL_HEIGHT:
                report.issues.append(
                    Issue(
                        "warning",
                        "cell-edge-touch",
                        f"Sprite pixels touch a cell edge at {location}.",
                        (
                            "Reframe the containing row with safe padding; "
                            "do not patch one final cell."
                        ),
                        location,
                    )
                )

        for column, row in sorted(unused, key=lambda item: (item[1], item[0])):
            location = f"row={row},column={column}"
            if alpha.crop(cell_box(column, row)).getbbox() is None:
                report.empty_unused_cells += 1
            else:
                report.issues.append(
                    Issue(
                        "error",
                        "unused-cell-populated",
                        f"Unused cell {location} contains visible pixels.",
                        "Clear the entire unused cell to transparent black.",
                        location,
                    )
                )

        report.hidden_rgb_pixels = _count_hidden_rgb(rgba)
        if report.hidden_rgb_pixels:
            report.issues.append(
                Issue(
                    "error",
                    "hidden-rgb",
                    f"{report.hidden_rgb_pixels} fully transparent pixels retain non-zero RGB.",
                    "Clear RGB to zero wherever alpha is zero, then re-encode losslessly.",
                    asset.image_path.name,
                )
            )
        report.chroma_pixels = _count_chroma(rgba, chroma_key)
        if report.chroma_pixels:
            report.issues.append(
                Issue(
                    "error",
                    "chroma-residue",
                    f"{report.chroma_pixels} visible pixels remain near the cyan generation key.",
                    "Run the approved edge-local despill once and validate the completed v2 atlas.",
                    asset.image_path.name,
                )
            )
        return report
