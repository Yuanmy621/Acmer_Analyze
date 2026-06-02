from __future__ import annotations

import unittest

from src.collector.codeforces_collector import (
    _build_contest_id,
    _build_problem_id,
    _build_problem_results,
    _derive_team_raw_name,
)


class CodeforcesCollectTest(unittest.TestCase):
    def test_build_identifiers(self) -> None:
        self.assertEqual(_build_contest_id(1987), "cf_1987")
        self.assertEqual(_build_problem_id(1987, "A"), "cf_1987_A")

    def test_derive_team_raw_name(self) -> None:
        party = {"members": [{"handle": "tourist"}, {"handle": "Benq"}]}
        self.assertEqual(_derive_team_raw_name(party), "tourist Benq")

    def test_build_problem_results(self) -> None:
        results, solved_count = _build_problem_results(
            1987,
            ["A", "B"],
            [
                {"points": 500.0, "rejectedAttemptCount": 1, "bestSubmissionTimeSeconds": 120},
                {"points": 0.0, "rejectedAttemptCount": 2},
            ],
        )

        self.assertEqual(solved_count, 1)
        self.assertTrue(results[0]["accepted"])
        self.assertEqual(results[0]["attempts"], 2)
        self.assertEqual(results[0]["first_ac_time"], 2)
        self.assertFalse(results[1]["accepted"])
        self.assertEqual(results[1]["attempts"], 2)
        self.assertIsNone(results[1]["first_ac_time"])


if __name__ == "__main__":
    unittest.main()
