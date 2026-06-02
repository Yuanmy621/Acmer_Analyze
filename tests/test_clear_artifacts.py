from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


class ClearArtifactsTest(unittest.TestCase):
    def test_clear_target_team_only_removes_team_specific_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            self._write(root_dir / "data" / "intermediate" / "team_identity" / "team_zju_alpha.json")
            self._write(root_dir / "outputs" / "reports" / "team_zju_alpha.html")
            self._write(root_dir / "outputs" / "reports" / "team_other.html")
            self._write(root_dir / "data" / "raw" / "contests" / "contests.json")

            result = self._run_clear(root_dir, "--target-team", "ZJU Alpha")

            self.assertEqual(result["canonical_id"], "team_zju_alpha")
            self.assertFalse((root_dir / "data" / "intermediate" / "team_identity" / "team_zju_alpha.json").exists())
            self.assertFalse((root_dir / "outputs" / "reports" / "team_zju_alpha.html").exists())
            self.assertTrue((root_dir / "outputs" / "reports" / "team_other.html").exists())
            self.assertTrue((root_dir / "data" / "raw" / "contests" / "contests.json").exists())

    def test_clear_all_removes_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            self._write(root_dir / "data" / "raw" / "contests" / "contests.json")
            self._write(root_dir / "data" / "normalized" / "standings" / "standings.json")
            self._write(root_dir / "outputs" / "reports" / "team_demo.html")
            self._write(root_dir / "outputs" / "visualizations" / "team_demo.json")

            result = self._run_clear(root_dir, "--all")

            self.assertEqual(result["mode"], "all")
            self.assertFalse((root_dir / "data" / "raw" / "contests" / "contests.json").exists())
            self.assertFalse((root_dir / "data" / "normalized" / "standings" / "standings.json").exists())
            self.assertFalse((root_dir / "outputs" / "reports" / "team_demo.html").exists())
            self.assertFalse((root_dir / "outputs" / "visualizations" / "team_demo.json").exists())

    def test_dry_run_does_not_delete_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            target_path = root_dir / "outputs" / "reports" / "team_zju_alpha.html"
            self._write(target_path)

            result = self._run_clear(root_dir, "--target-team", "ZJU Alpha", "--dry-run")

            self.assertTrue(result["dry_run"])
            self.assertTrue(target_path.exists())
            self.assertIn("outputs/reports/team_zju_alpha.html", result["deleted"])

    def _write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")

    def _run_clear(self, root_dir: Path, *args: str) -> dict:
        command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "clear_artifacts.py"),
            *args,
        ]
        completed = subprocess.run(
            command,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
