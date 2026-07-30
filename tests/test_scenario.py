from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scales_pet.scenario import load_scenario, render_scenario

from .helpers import make_pet


class ScenarioTests(unittest.TestCase):
    def test_replay_renders_real_atlas_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pet = make_pet(root / "pet")
            scenario = root / "scenario.json"
            scenario.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "background": "#112233",
                        "events": [
                            {"state": "idle", "loops": 1, "frame_ms": 80},
                            {"direction": "90", "hold_ms": 400},
                            {"state": "needs-input", "loops": 1, "frame_ms": 90},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "replay.gif"
            result = render_scenario(pet, scenario, output)
            with Image.open(output) as animation:
                frame_count = animation.n_frames

        self.assertTrue(result["ok"])
        self.assertEqual(result["frames"], 13)
        self.assertEqual(frame_count, 13)
        self.assertIn("look-90", result["states"])

    def test_unknown_state_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.json"
            scenario.write_text(
                '{"events":[{"state":"teleport","loops":1}]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown state"):
                load_scenario(scenario)


if __name__ == "__main__":
    unittest.main()
