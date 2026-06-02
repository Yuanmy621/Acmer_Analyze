from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


class PipelineSmokeTest(unittest.TestCase):
    def _run_with_retry(self, command: list[str], retries: int = 3) -> subprocess.CompletedProcess[str]:
        last_error: subprocess.CalledProcessError | None = None
        for _ in range(retries):
            try:
                return subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as error:
                last_error = error
        if last_error is None:
            raise AssertionError("unexpected retry state")
        raise last_error

    def test_pipeline_smoke(self) -> None:
        command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "run_pipeline.py"),
            "--task-file",
            str(ROOT_DIR / "examples" / "sample_task.json"),
            "--skip-analyze",
        ]
        completed = self._run_with_retry(command)
        result = json.loads(completed.stdout)

        self.assertEqual(result["canonical_id"], "team_zju_alpha")
        self.assertIn("validate_final", result["executed_stages"])
        self.assertNotIn("analyze", result["executed_stages"])

        report_path = ROOT_DIR / "outputs" / "reports" / "team_zju_alpha.md"
        report_html_path = ROOT_DIR / "outputs" / "reports" / "team_zju_alpha.html"
        visualization_html_path = ROOT_DIR / "outputs" / "visualizations" / "team_zju_alpha.html"
        validation_path = ROOT_DIR / "outputs" / "validation" / "team_zju_alpha.json"

        self.assertTrue(report_path.exists())
        self.assertTrue(report_html_path.exists())
        self.assertTrue(visualization_html_path.exists())
        self.assertTrue(validation_path.exists())

        report_content = report_path.read_text(encoding="utf-8")
        report_html_content = report_html_path.read_text(encoding="utf-8")
        visualization_html_content = visualization_html_path.read_text(encoding="utf-8")
        self.assertIn("## 1. 概览", report_content)
        self.assertIn("排名走势", report_html_content)
        self.assertIn("题型热区", report_html_content)
        self.assertIn("能力雷达", report_html_content)
        self.assertIn("比赛时间轴", report_html_content)
        self.assertIn("训练重点矩阵", report_html_content)
        self.assertIn("Single Page Analysis Site", report_html_content)
        self.assertIn("Visual Analysis Board", visualization_html_content)

        validation_payload = json.loads(validation_path.read_text(encoding="utf-8"))
        self.assertTrue(validation_payload["passed"])

    def test_codeforces_collect_and_normalize(self) -> None:
        command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "run_pipeline.py"),
            "--task-file",
            str(ROOT_DIR / "examples" / "codeforces_task.json"),
            "--end-stage",
            "normalize",
            "--skip-analyze",
            "--skip-visualize",
        ]
        completed = self._run_with_retry(command)
        result = json.loads(completed.stdout)

        self.assertEqual(result["canonical_id"], "team_tourist")
        self.assertIn("collect", result["executed_stages"])
        self.assertIn("normalize", result["executed_stages"])

        contests_path = ROOT_DIR / "data" / "normalized" / "contests" / "contests.json"
        standings_path = ROOT_DIR / "data" / "normalized" / "standings" / "standings.json"
        problems_path = ROOT_DIR / "data" / "normalized" / "problems" / "problems.json"

        contests = json.loads(contests_path.read_text(encoding="utf-8"))
        standings = json.loads(standings_path.read_text(encoding="utf-8"))
        problems = json.loads(problems_path.read_text(encoding="utf-8"))

        self.assertTrue(contests)
        self.assertTrue(standings)
        self.assertTrue(problems)
        self.assertEqual(contests[0]["source"], "codeforces")
        self.assertTrue(contests[0]["contest_id"].startswith("cf_"))
        self.assertTrue(any(item["team_raw_name"] == "tourist" for item in standings))

    def test_dynamic_codeforces_args(self) -> None:
        command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "run_pipeline.py"),
            "--source",
            "codeforces",
            "--target-team",
            "tourist",
            "--codeforces-handle",
            "tourist",
            "--max-contests",
            "1",
            "--end-stage",
            "normalize",
            "--skip-analyze",
            "--skip-visualize",
        ]
        completed = self._run_with_retry(command)
        result = json.loads(completed.stdout)

        self.assertEqual(result["canonical_id"], "team_tourist")
        self.assertIn("collect", result["executed_stages"])
        self.assertIn("normalize", result["executed_stages"])


if __name__ == "__main__":
    unittest.main()
