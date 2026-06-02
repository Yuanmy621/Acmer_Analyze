from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


class PipelineHooksTest(unittest.TestCase):
    def test_pipeline_emits_hook_logs(self) -> None:
        command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "run_pipeline.py"),
            "--task-file",
            str(ROOT_DIR / "examples" / "sample_task.json"),
            "--skip-analyze",
            "--skip-visualize",
        ]
        subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, check=True)

        run_log = ROOT_DIR / ".claude" / "hooks" / "outputs" / "run_logs" / "run_events.jsonl"
        stage_log = ROOT_DIR / ".claude" / "hooks" / "outputs" / "stage_logs" / "stage_events.jsonl"

        self.assertTrue(run_log.exists())
        self.assertTrue(stage_log.exists())

        run_lines = [json.loads(line) for line in run_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        stage_lines = [json.loads(line) for line in stage_log.read_text(encoding="utf-8").splitlines() if line.strip()]

        self.assertTrue(any(item["event_name"] == "run.before_start" for item in run_lines))
        self.assertTrue(any(item["event_name"] == "run.after_finish" for item in run_lines))
        self.assertTrue(any(item["event_name"] == "stage.before" for item in stage_lines))
        self.assertTrue(any(item["event_name"] == "stage.after" for item in stage_lines))


if __name__ == "__main__":
    unittest.main()
