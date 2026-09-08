#!/usr/bin/env python3
"""Exercise the actual native detector, optionally with externally supplied games."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BINARY = Path(os.environ.get("SCUMMVM_DETECTOR", ROOT / ".retrom/native/scummvm"))


def detect(path, recursive=False):
    args = [str(BINARY), "--config=/dev/null", "--retrom-detect", f"--path={path}"]
    if recursive:
        args.append("--recursive")
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return result, json.loads(result.stdout) if result.stdout else None


class DetectorTests(unittest.TestCase):
    def test_empty_directory_is_valid_without_candidates(self):
        with tempfile.TemporaryDirectory() as root:
            result, document = detect(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(document["schemaVersion"], 1)
        self.assertEqual(document["upstreamCommit"], "fed42f2068dcafc6aafa1c28c77e4c88def74b66")
        self.assertEqual(document["candidates"], [])
        self.assertIsNone(document["error"])

    def test_missing_path_is_an_error_not_empty_success(self):
        with tempfile.TemporaryDirectory() as root:
            result, document = detect(Path(root) / "missing")
        self.assertNotEqual(result.returncode, 0)
        # The upstream CLI validates --path before dispatching commands.
        self.assertTrue(document is None or document["error"] == "SCUMMVM_DETECTION_PATH_INVALID")

    def test_recursive_scan_is_bounded_and_discards_partial_candidates(self):
        with tempfile.TemporaryDirectory() as root:
            current = Path(root)
            for _ in range(34):
                current /= "nested"
                current.mkdir()
            result, document = detect(root, recursive=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(document["error"], "SCUMMVM_DETECTION_LIMIT_EXCEEDED")
        self.assertEqual(document["candidates"], [])

    @unittest.skipUnless(os.environ.get("SCUMMVM_TEST_GAMES"), "external public games not configured")
    def test_public_games_keep_all_roots_and_launch_hints(self):
        result, document = detect(os.environ["SCUMMVM_TEST_GAMES"], recursive=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        candidates = document["candidates"]
        self.assertTrue({"sky", "queen", "drascula"}.issubset({c["engineId"] for c in candidates}))
        for candidate in candidates:
            self.assertFalse(candidate["root"].startswith("/"))
            self.assertNotIn("..", candidate["root"].split("/"))
            for field in ["gameId", "language", "platform", "extra", "preferredTarget", "guiOptions"]:
                self.assertIsInstance(candidate[field], str)
            self.assertIsInstance(candidate["config"], dict)
            self.assertIsInstance(candidate["canBeAdded"], bool)
        self.assertGreaterEqual(len({c["root"] for c in candidates}), 3)


if __name__ == "__main__":
    unittest.main()
