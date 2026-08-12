#!/usr/bin/env python3
"""Render the 16 v2 look-direction cells as a deterministic looping GIF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

from scales_pet.model import (
    CELL_HEIGHT,
    CELL_WIDTH,
    LOOK_DIRECTIONS,
    TARGETS,
    direction_cell,
    resolve_asset,
)


def render_direction_sweep(
    source: str | Path,
    output: str | Path,
    *,
    duration_ms: int = 160,
) -> dict[str, Any]:
    if duration_ms < 20 or duration_ms > 10_000:
        raise ValueError("duration_ms must be between 20 and 10000")

    asset = resolve_asset(source)
    output_path = Path(output).expanduser().resolve()
    with Image.open(asset.image_path) as opened:
        opened.load()
        if opened.size != TARGETS["desktop"].dimensions:
            raise ValueError(
                "direction sweep requires a 1536x2288 desktop v2 atlas"
            )
        rgba = opened.convert("RGBA")
        frames = [
            rgba.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            for column, row in (direction_cell(direction) for direction in LOOK_DIRECTIONS)
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[duration_ms] * len(frames),
        loop=0,
        disposal=2,
        optimize=False,
    )
    return {
        "ok": True,
        "source": str(asset.image_path),
        "output": str(output_path),
        "frames": len(frames),
        "directions": list(LOOK_DIRECTIONS),
        "duration_ms": duration_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Desktop v2 pet directory, manifest, PNG, or WebP")
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration-ms", type=int, default=160)
    args = parser.parse_args()
    print(
        json.dumps(
            render_direction_sweep(
                args.source,
                args.output,
                duration_ms=args.duration_ms,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
