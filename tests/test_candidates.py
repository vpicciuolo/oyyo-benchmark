import unittest

from oyyo_benchmark.candidates import evaluate_candidate, rank_candidates


MATRIX = {
    "hard_gates": [
        {"id": "rights"},
        {"id": "runtime"},
    ],
    "family_profiles": {
        "mini": {
            "metrics": [
                {
                    "id": "quality",
                    "direction": "higher_is_better",
                    "min": 0,
                    "max": 100,
                    "weight": 0.75,
                },
                {
                    "id": "ram",
                    "direction": "lower_is_better",
                    "min": 4,
                    "max": 16,
                    "weight": 0.25,
                },
            ]
        }
    },
}


def candidate(candidate_id="a", quality=80, ram=8):
    return {
        "candidate_id": candidate_id,
        "family": "mini",
        "hard_gates": {"rights": True, "runtime": True},
        "metrics": {"quality": quality, "ram": ram},
    }


class CandidateEvaluationTest(unittest.TestCase):
    def test_eligible_candidate_scores(self):
        result = evaluate_candidate(candidate(), MATRIX)
        self.assertTrue(result.eligible)
        self.assertIsNotNone(result.score)
        self.assertEqual(result.hard_gate_failures, [])
        self.assertEqual(result.missing_metrics, [])

    def test_hard_gate_failure_blocks_ranking(self):
        data = candidate()
        data["hard_gates"]["runtime"] = False
        result = evaluate_candidate(data, MATRIX)
        self.assertFalse(result.eligible)
        self.assertIsNone(result.score)
        self.assertEqual(result.hard_gate_failures, ["runtime"])

    def test_missing_metric_blocks_ranking(self):
        data = candidate()
        del data["metrics"]["ram"]
        result = evaluate_candidate(data, MATRIX)
        self.assertFalse(result.eligible)
        self.assertEqual(result.missing_metrics, ["ram"])

    def test_lower_is_better_metric_changes_order(self):
        low_ram = candidate("low-ram", quality=80, ram=4)
        high_ram = candidate("high-ram", quality=80, ram=16)
        ranked = rank_candidates([high_ram, low_ram], MATRIX)
        self.assertEqual(ranked[0].candidate_id, "low-ram")

    def test_ineligible_candidates_rank_after_eligible(self):
        eligible = candidate("eligible", quality=60, ram=16)
        blocked = candidate("blocked", quality=100, ram=4)
        blocked["hard_gates"]["rights"] = False
        ranked = rank_candidates([blocked, eligible], MATRIX)
        self.assertEqual(ranked[0].candidate_id, "eligible")
        self.assertTrue(ranked[0].eligible)


if __name__ == "__main__":
    unittest.main()
