from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.models.schemas import AnalysisTask
from src.orchestrator.context import PipelineContext
from src.report.markdown_report import run_report
from src.visualize.chart_data import run_visualize
from src.validation.validator import run_validate_final
from src.models.serde import write_json


ROOT_DIR = Path(__file__).resolve().parents[1]


class DeliveryHooksTest(unittest.TestCase):
    def test_delivery_hooks_emit_validation_summary(self) -> None:
        validation_log = ROOT_DIR / '.claude' / 'hooks' / 'outputs' / 'validation' / 'validation_events.jsonl'
        if validation_log.exists():
            validation_log.unlink()

        context = PipelineContext(root_dir=ROOT_DIR, task=AnalysisTask(target_team='Hook Delivery'))
        canonical_id = context.canonical_id

        write_json(
            ROOT_DIR / 'data' / 'derived' / 'team_metrics' / f'{canonical_id}.json',
            {
                'canonical_id': canonical_id,
                'rank_trend': [{'contest_id': 'cf_1', 'rank': 1, 'percentile_rank': 1.0}],
                'tag_distribution': {'implementation': {'attempted': 1, 'solved': 1, 'solve_rate': 1.0}},
                'stability_score': 1.0,
                'growth_score': 1.0,
                'solve_pace': {'avg_first_ac_minute': 2.0, 'late_stage_solve_ratio': 0.0},
            },
        )
        write_json(
            ROOT_DIR / 'outputs' / 'insights' / f'{canonical_id}.json',
            {
                'canonical_id': canonical_id,
                'strengths': ['实现题稳定'],
                'weaknesses': ['样本较少'],
                'summary': '测试摘要',
                'training_advice': ['继续观察'],
                'stage_analysis': '测试阶段分析',
                'model_used': 'rule-based-template',
                'generated_at': '2026-06-02T00:00:00Z',
            },
        )
        write_json(
            ROOT_DIR / 'data' / 'intermediate' / 'team_history' / f'{canonical_id}.json',
            {
                'canonical_id': canonical_id,
                'contest_records': [{'contest_id': 'cf_1', 'rank': 1, 'solved_count': 1, 'total_teams': 1, 'percentile_rank': 1.0, 'problem_results': []}],
            },
        )

        run_report(context)
        run_visualize(context)
        run_validate_final(context)

        self.assertTrue(validation_log.exists())
        lines = [json.loads(line) for line in validation_log.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.assertTrue(any(item['event_name'] == 'report.after_generate' for item in lines))
        self.assertTrue(any(item['event_name'] == 'visualize.after_generate' for item in lines))
        self.assertTrue(any(item['event_name'] == 'validation.after_validate' for item in lines))


if __name__ == '__main__':
    unittest.main()
