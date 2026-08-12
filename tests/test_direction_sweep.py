from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.render_direction_sweep import render_direction_sweep

from .helpers import make_pet


class DirectionSweepTests(unittest.TestCase):
    def test_renders_all_sixteen_v2_direction_cells(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pet = make_pet(root / "pet")
            output = root / "look-directions.gif"
            result = render_direction_sweep(pet, output, duration_ms=120)

            with Image.open(output) as rendered:
                self.assertEqual(rendered.size, (192, 208))
                self.assertEqual(rendered.n_frames, 16)

        self.assertTrue(result["ok"])
        self.assertEqual(result["frames"], 16)
        self.assertEqual(result["duration_ms"], 120)

    def test_rejects_unsafe_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "duration_ms"):
            render_direction_sweep("not-read", "not-written", duration_ms=10)


if __name__ == "__main__":
    unittest.main()
