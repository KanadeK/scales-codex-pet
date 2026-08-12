from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
MAX_FILE_BYTES = 20 * 1024 * 1024
NEUTRAL_LOOK_CELL = (6, 0)


@dataclass(frozen=True, slots=True)
class RowSpec:
    name: str
    row: int
    frames: int
    purpose: str


STANDARD_ROWS = (
    RowSpec("idle", 0, 6, "calm resting loop"),
    RowSpec("running-right", 1, 8, "rightward drag movement"),
    RowSpec("running-left", 2, 8, "leftward drag movement"),
    RowSpec("waving", 3, 4, "wake or greeting"),
    RowSpec("jumping", 4, 5, "ready or celebratory jump"),
    RowSpec("failed", 5, 8, "blocked or failed reaction"),
    RowSpec("waiting", 6, 6, "needs input"),
    RowSpec("running", 7, 6, "active task work"),
    RowSpec("review", 8, 6, "completed work awaiting review"),
)

LOOK_DIRECTIONS = (
    "000",
    "022.5",
    "045",
    "067.5",
    "090",
    "112.5",
    "135",
    "157.5",
    "180",
    "202.5",
    "225",
    "247.5",
    "270",
    "292.5",
    "315",
    "337.5",
)

LOOK_ROWS = (
    RowSpec("look-row-9", 9, 8, "000 through 157.5 degrees"),
    RowSpec("look-row-10", 10, 8, "180 through 337.5 degrees"),
)


@dataclass(frozen=True, slots=True)
class TargetSpec:
    name: str
    rows: int
    sprite_version: int | None
    row_specs: tuple[RowSpec, ...]
    description: str

    @property
    def width(self) -> int:
        return COLUMNS * CELL_WIDTH

    @property
    def height(self) -> int:
        return self.rows * CELL_HEIGHT

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.width, self.height


TARGETS = {
    "desktop": TargetSpec(
        name="desktop",
        rows=11,
        sprite_version=2,
        row_specs=STANDARD_ROWS + LOOK_ROWS,
        description="Local Codex desktop and compatible CLI v2 pet",
    ),
    "web": TargetSpec(
        name="web",
        rows=9,
        sprite_version=None,
        row_specs=STANDARD_ROWS,
        description="ChatGPT web custom-pet upload atlas",
    ),
}

STATE_ALIASES = {
    "idle": "idle",
    "wake": "waving",
    "waving": "waving",
    "move-right": "running-right",
    "running-right": "running-right",
    "move-left": "running-left",
    "running-left": "running-left",
    "ready": "jumping",
    "jumping": "jumping",
    "blocked": "failed",
    "failed": "failed",
    "needs-input": "waiting",
    "waiting": "waiting",
    "running": "running",
    "review": "review",
    "complete": "review",
}


@dataclass(frozen=True, slots=True)
class ResolvedAsset:
    source: Path
    image_path: Path
    manifest_path: Path | None
    manifest: dict[str, Any] | None


def cell_box(column: int, row: int) -> tuple[int, int, int, int]:
    return (
        column * CELL_WIDTH,
        row * CELL_HEIGHT,
        (column + 1) * CELL_WIDTH,
        (row + 1) * CELL_HEIGHT,
    )


def required_cells(target: TargetSpec) -> set[tuple[int, int]]:
    cells = {
        (column, row.row)
        for row in target.row_specs
        for column in range(row.frames)
    }
    if target.name == "desktop":
        cells.add(NEUTRAL_LOOK_CELL)
    return cells


def optional_cells(target: TargetSpec) -> set[tuple[int, int]]:
    if target.name == "web":
        return {NEUTRAL_LOOK_CELL}
    return set()


def unused_cells(target: TargetSpec) -> set[tuple[int, int]]:
    used = required_cells(target) | optional_cells(target)
    return {
        (column, row)
        for row in range(target.rows)
        for column in range(COLUMNS)
        if (column, row) not in used
    }


def infer_target(dimensions: tuple[int, int]) -> TargetSpec | None:
    for target in TARGETS.values():
        if target.dimensions == dimensions:
            return target
    return None


def row_by_name(name: str) -> RowSpec:
    normalized = STATE_ALIASES.get(name, name)
    for row in STANDARD_ROWS + LOOK_ROWS:
        if row.name == normalized:
            return row
    raise KeyError(f"unknown animation state: {name}")


def direction_cell(direction: str | float | int) -> tuple[int, int]:
    numeric = float(direction)
    values = tuple(float(value) for value in LOOK_DIRECTIONS)
    try:
        index = values.index(numeric)
    except ValueError as error:
        raise KeyError(f"unsupported look direction: {direction}") from error
    return index % COLUMNS, 9 + index // COLUMNS


def resolve_asset(source: str | Path) -> ResolvedAsset:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"source does not exist: {path}")

    if path.is_dir():
        manifest_path = path / "pet.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"pet directory is missing pet.json: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        relative = manifest.get("spritesheetPath", "spritesheet.webp")
        image_path = (path / str(relative)).resolve()
        if path not in image_path.parents:
            raise ValueError("spritesheetPath escapes the pet directory")
        if not image_path.is_file():
            raise FileNotFoundError(f"manifest spritesheet is missing: {image_path}")
        return ResolvedAsset(path, image_path, manifest_path, manifest)

    if path.name == "pet.json":
        return resolve_asset(path.parent)

    if path.suffix.lower() not in {".png", ".webp"}:
        raise ValueError("source must be a pet directory, pet.json, PNG, or WebP")
    return ResolvedAsset(path, path, None, None)
