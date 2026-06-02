from __future__ import annotations

import unittest

from src.metrics.builder import _build_stability_score, _build_tag_distribution


class MetricsBuilderTest(unittest.TestCase):
    def test_build_tag_distribution(self) -> None:
        records = [
            {
                "problem_results": [
                    {"problem_id": "p1", "accepted": True},
                    {"problem_id": "p2", "accepted": False},
                ]
            }
        ]
        problems = {
            "p1": {"tags": ["implementation"]},
            "p2": {"tags": ["graph"]},
        }

        distribution = _build_tag_distribution(records, problems)

        self.assertEqual(distribution["implementation"]["solved"], 1)
        self.assertEqual(distribution["implementation"]["attempted"], 1)
        self.assertEqual(distribution["implementation"]["solve_rate"], 1.0)
        self.assertEqual(distribution["graph"]["solved"], 0)

    def test_build_stability_score_range(self) -> None:
        records = [
            {"percentile_rank": 0.9},
            {"percentile_rank": 0.8},
            {"percentile_rank": 0.85},
        ]

        score = _build_stability_score(records)

        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
