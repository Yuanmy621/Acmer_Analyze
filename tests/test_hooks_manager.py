from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.models.schemas import AnalysisTask
from src.models.serde import write_json
from src.orchestrator.context import PipelineContext


ROOT_DIR = Path(__file__).resolve().parents[1]


class HooksManagerTest(unittest.TestCase):
    def test_hook_manager_loads_bindings(self) -> None:
        context = PipelineContext(root_dir=ROOT_DIR, task=AnalysisTask(target_team="Hook Demo"))
        manager = context.hook_manager()

        self.assertTrue(manager.enabled)
        self.assertIn("run.before_start", manager.config["bindings"])
        self.assertIn("stage.before", manager.config["bindings"])

    def test_hook_context_contains_run_id(self) -> None:
        context = PipelineContext(root_dir=ROOT_DIR, task=AnalysisTask(target_team="Hook Demo"))
        hook_context = context.new_hook_context("run.before_start")

        self.assertTrue(hook_context.run_id.startswith("run_"))
        self.assertEqual(hook_context.canonical_id, "team_hook_demo")

    def test_artifact_hook_writes_manifest(self) -> None:
        artifact_log = ROOT_DIR / '.claude' / 'hooks' / 'outputs' / 'artifacts' / 'artifact_events.jsonl'
        if artifact_log.exists():
            artifact_log.unlink()

        write_json(ROOT_DIR / 'data' / 'raw' / 'contests' / 'hooks_test.json', [{"ok": True}])

        self.assertTrue(artifact_log.exists())
        lines = [json.loads(line) for line in artifact_log.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.assertTrue(any(item['event_name'] == 'artifact.after_write' for item in lines))


if __name__ == "__main__":
    unittest.main()
