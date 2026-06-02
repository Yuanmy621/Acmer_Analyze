from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analyzer.insight_generator import run_analyze
from src.analyzer.llm_client import LlmConfigError, load_llm_config
from src.models.schemas import AnalysisTask
from src.models.serde import write_json
from src.orchestrator.context import PipelineContext


class LlmAnalyzeTest(unittest.TestCase):
    def test_load_llm_config_from_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "env": {
                            "ANTHROPIC_BASE_URL": "https://example.test/llm",
                            "ANTHROPIC_AUTH_TOKEN": "token-123",
                            "ANTHROPIC_MODEL": "gpt-test",
                        },
                        "model": "fallback-model",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                config = load_llm_config(settings_path=str(settings_path))

            self.assertEqual(config.base_url, "https://example.test/llm")
            self.assertEqual(config.auth_token, "token-123")
            self.assertEqual(config.model, "gpt-test")
            self.assertEqual(config.settings_path, str(settings_path))

    def test_load_llm_config_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(json.dumps({"env": {}}, ensure_ascii=False), encoding="utf-8")

            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(LlmConfigError):
                    load_llm_config(settings_path=str(settings_path))

    def test_analysis_task_defaults_to_enable_llm(self) -> None:
        task = AnalysisTask(target_team="demo")
        self.assertTrue(task.enable_llm_insight)

    def test_run_analyze_with_llm_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            context = self._prepare_context(root_dir, enable_llm_insight=True)

            with patch("src.analyzer.insight_generator.invoke_llm") as invoke_mock:
                invoke_mock.return_value = (
                    json.dumps(
                        {
                            "summary": "队伍近期整体呈稳中有升趋势。",
                            "strengths": ["implementation 题处理稳定", "中前期拿分效率较高"],
                            "weaknesses": ["trees 题型突破不足", "高难题后程追分能力较弱"],
                            "training_advice": ["加强树上题专项训练", "增加高压赛时复盘"],
                            "stage_analysis": "当前队伍具备稳定拿基础分的能力，但在中高难题上仍有提升空间。",
                        },
                        ensure_ascii=False,
                    ),
                    type("Config", (), {"model": "gpt-test", "settings_path": "/tmp/settings.json"})(),
                )

                run_analyze(context)

            payload = self._read_insight(root_dir)
            self.assertEqual(payload["model_used"], "gpt-test")
            self.assertEqual(payload["llm_provider"], "anthropic-compatible")
            self.assertIn("implementation", payload["strengths"][0])

    def test_run_analyze_raises_on_llm_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            context = self._prepare_context(root_dir, enable_llm_insight=True)

            with patch("src.analyzer.insight_generator.invoke_llm", side_effect=LlmConfigError("missing config")):
                with self.assertRaises(LlmConfigError):
                    run_analyze(context)

    def test_run_analyze_uses_llm_even_when_legacy_disable_flag_is_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            context = self._prepare_context(root_dir, enable_llm_insight=False)

            with patch("src.analyzer.insight_generator.invoke_llm") as invoke_mock:
                invoke_mock.return_value = (
                    json.dumps(
                        {
                            "summary": "队伍分析由 LLM 生成。",
                            "strengths": ["基础题稳定", "配合节奏清晰"],
                            "weaknesses": ["高难题突破不足", "后程追分空间较大"],
                            "training_advice": ["保持专题训练", "加强赛后复盘"],
                            "stage_analysis": "当前阶段适合继续通过结构化训练提高上限。",
                        },
                        ensure_ascii=False,
                    ),
                    type("Config", (), {"model": "gpt-test", "settings_path": "/tmp/settings.json"})(),
                )

                run_analyze(context)

            payload = self._read_insight(root_dir)
            self.assertEqual(payload["model_used"], "gpt-test")
            invoke_mock.assert_called_once()

    def test_run_analyze_raises_even_when_legacy_fallback_flag_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            context = self._prepare_context(root_dir, enable_llm_insight=True, llm_fallback_to_rule=True)

            with patch("src.analyzer.insight_generator.invoke_llm", side_effect=LlmConfigError("missing config")):
                with self.assertRaises(LlmConfigError):
                    run_analyze(context)

    def _prepare_context(
        self,
        root_dir: Path,
        *,
        enable_llm_insight: bool,
        llm_fallback_to_rule: bool = True,
    ) -> PipelineContext:
        task = AnalysisTask(
            target_team="ZJU Alpha",
            aliases=["zju_alpha", "ZJU-Alpha"],
            source="fixture",
            time_range="2026-Q1",
            fixture_dir="examples/sample_fixture",
            generate_visualize=True,
            generate_insight=True,
            enable_llm_insight=enable_llm_insight,
            llm_fallback_to_rule=llm_fallback_to_rule,
            school="Zhejiang University",
            region="CN",
        )
        context = PipelineContext(root_dir=root_dir, task=task)

        canonical_id = context.canonical_id
        write_json(
            root_dir / "data" / "derived" / "team_metrics" / f"{canonical_id}.json",
            {
                "canonical_id": canonical_id,
                "rank_trend": [
                    {"contest_id": "cf_1987", "rank": 12, "percentile_rank": 0.6667},
                    {"contest_id": "ucup_2026_stage1", "rank": 8, "percentile_rank": 0.75},
                ],
                "tag_distribution": {
                    "implementation": {"attempted": 1, "solved": 1, "solve_rate": 1.0},
                    "graph": {"attempted": 1, "solved": 1, "solve_rate": 1.0},
                    "bitmasks": {"attempted": 1, "solved": 1, "solve_rate": 1.0},
                    "trees": {"attempted": 1, "solved": 0, "solve_rate": 0.0},
                },
                "stability_score": 0.9583,
                "growth_score": 0.5416,
                "solve_pace": {
                    "avg_first_ac_minute": 37.67,
                    "late_stage_solve_ratio": 0.0,
                },
            },
        )
        write_json(
            root_dir / "data" / "intermediate" / "team_identity" / f"{canonical_id}.json",
            {
                "canonical_id": canonical_id,
                "display_name": "ZJU Alpha",
                "aliases": ["ZJU Alpha", "zju_alpha", "ZJU-Alpha"],
                "platform_ids": {"fixture": canonical_id},
                "school": "Zhejiang University",
                "region": "CN",
                "matched_names": ["ZJU Alpha", "zju_alpha"],
            },
        )
        write_json(
            root_dir / "data" / "intermediate" / "team_history" / f"{canonical_id}.json",
            {
                "canonical_id": canonical_id,
                "contest_records": [
                    {
                        "contest_id": "cf_1987",
                        "rank": 12,
                        "solved_count": 2,
                        "total_teams": 3,
                        "percentile_rank": 0.6667,
                        "problem_results": [
                            {"problem_id": "cf_1987_A", "accepted": True, "attempts": 1, "first_ac_time": 10},
                            {"problem_id": "cf_1987_B", "accepted": True, "attempts": 2, "first_ac_time": 85},
                        ],
                    },
                    {
                        "contest_id": "ucup_2026_stage1",
                        "rank": 8,
                        "solved_count": 1,
                        "total_teams": 3,
                        "percentile_rank": 0.75,
                        "problem_results": [
                            {"problem_id": "ucup_2026_stage1_A", "accepted": True, "attempts": 1, "first_ac_time": 18},
                            {"problem_id": "ucup_2026_stage1_B", "accepted": False, "attempts": 3, "first_ac_time": None},
                        ],
                    },
                ],
            },
        )
        return context

    def _read_insight(self, root_dir: Path) -> dict:
        return json.loads((root_dir / "outputs" / "insights" / "team_zju_alpha.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
