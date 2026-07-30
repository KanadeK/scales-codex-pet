from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor

from .model import (
    CELL_HEIGHT,
    CELL_WIDTH,
    STATE_ALIASES,
    cell_box,
    direction_cell,
    resolve_asset,
    row_by_name,
)
from .validation import validate_source


@dataclass(frozen=True, slots=True)
class ScenarioFrame:
    image: Image.Image
    duration_ms: int
    label: str


def load_scenario(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scenario root must be an object")
    validate_scenario(data)
    return data


def validate_scenario(data: dict[str, Any]) -> None:
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("scenario events must be a non-empty list")
    if len(events) > 100:
        raise ValueError("scenario may contain at most 100 events")

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"event {index} must be an object")
        has_state = isinstance(event.get("state"), str)
        has_direction = "direction" in event
        if has_state == has_direction:
            raise ValueError(f"event {index} must define exactly one of state or direction")
        if has_state:
            state = str(event["state"])
            if state not in STATE_ALIASES:
                raise ValueError(f"event {index} uses unknown state {state!r}")
            loops = event.get("loops", 1)
            if not isinstance(loops, int) or not 1 <= loops <= 20:
                raise ValueError(f"event {index} loops must be an integer from 1 to 20")
        else:
            direction_cell(event["direction"])
            hold_ms = event.get("hold_ms", 600)
            if not isinstance(hold_ms, int) or not 40 <= hold_ms <= 10_000:
                raise ValueError(f"event {index} hold_ms must be 40..10000")
        frame_ms = event.get("frame_ms", 120)
        if not isinstance(frame_ms, int) or not 40 <= frame_ms <= 2_000:
            raise ValueError(f"event {index} frame_ms must be 40..2000")


def _composite_cell(
    atlas: Image.Image,
    column: int,
    row: int,
    background: tuple[int, int, int],
    scale: int,
) -> Image.Image:
    cell = atlas.crop(cell_box(column, row)).convert("RGBA")
    canvas = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (*background, 255))
    canvas.alpha_composite(cell)
    if scale != 1:
        canvas = canvas.resize(
            (CELL_WIDTH * scale, CELL_HEIGHT * scale),
            Image.Resampling.NEAREST,
        )
    return canvas.convert("RGB")


def scenario_frames(
    source: str | Path,
    scenario: dict[str, Any],
    *,
    scale: int = 1,
) -> list[ScenarioFrame]:
    if scale not in {1, 2, 3, 4}:
        raise ValueError("scale must be 1, 2, 3, or 4")
    validate_scenario(scenario)
    report = validate_source(source, target_name="desktop")
    if not report.ok:
        raise ValueError(f"cannot replay an invalid desktop atlas: {report.to_dict()}")

    background_value = scenario.get("background", "#17212b")
    if not isinstance(background_value, str):
        raise ValueError("scenario background must be a CSS-style color string")
    parsed_background = ImageColor.getrgb(background_value)
    background = (
        int(parsed_background[0]),
        int(parsed_background[1]),
        int(parsed_background[2]),
    )
    asset = resolve_asset(source)
    frames: list[ScenarioFrame] = []
    with Image.open(asset.image_path) as opened:
        atlas = opened.convert("RGBA")
        for event in scenario["events"]:
            frame_ms = int(event.get("frame_ms", 120))
            if "direction" in event:
                column, row = direction_cell(event["direction"])
                frames.append(
                    ScenarioFrame(
                        _composite_cell(atlas, column, row, background, scale),
                        int(event.get("hold_ms", 600)),
                        f"look-{event['direction']}",
                    )
                )
                continue

            state = STATE_ALIASES[str(event["state"])]
            row_spec = row_by_name(state)
            for _loop in range(int(event.get("loops", 1))):
                for column in range(row_spec.frames):
                    frames.append(
                        ScenarioFrame(
                            _composite_cell(atlas, column, row_spec.row, background, scale),
                            frame_ms,
                            state,
                        )
                    )
    if len(frames) > 1_000:
        raise ValueError("expanded scenario exceeds the 1000-frame safety limit")
    return frames


def render_scenario(
    source: str | Path,
    scenario_path: str | Path,
    output: str | Path,
    *,
    scale: int = 1,
) -> dict[str, Any]:
    scenario = load_scenario(scenario_path)
    frames = scenario_frames(source, scenario, scale=scale)
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    first, *rest = frames
    first.image.save(
        destination,
        "GIF",
        save_all=True,
        append_images=[frame.image for frame in rest],
        duration=[frame.duration_ms for frame in frames],
        loop=0,
        optimize=False,
        disposal=2,
    )
    return {
        "ok": True,
        "scenario": str(Path(scenario_path).expanduser().resolve()),
        "output": str(destination),
        "frames": len(frames),
        "duration_ms": sum(frame.duration_ms for frame in frames),
        "states": sorted({frame.label for frame in frames}),
        "size": list(first.image.size),
    }
