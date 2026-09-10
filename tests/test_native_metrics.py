from __future__ import annotations

import unittest

from oyyo_benchmark.native_metrics import evaluate_native_metrics


class NativeMetricsTest(unittest.TestCase):
    def suite(self):
        return {
            "schema_version": "0.1",
            "metrics": {
                "quality_score": {
                    "cases": [
                        {"id": "q1", "validator": "exact_text", "expected": "9"},
                        {"id": "q2", "validator": "exact_text", "expected": "DENY"},
                    ]
                },
                "multilingual_semantic_score": {
                    "cases": [
                        {
                            "id": "m1",
                            "validator": "accepted_texts",
                            "accepted": ["Ciao", "Salve"],
                        }
                    ]
                },
                "tool_structured_reliability_pct": {
                    "cases": [
                        {
                            "id": "t1",
                            "validator": "exact_json",
                            "expected": {"type": "final", "content": "OK"},
                        }
                    ]
                },
                "coding_score": {
                    "cases": [
                        {"id": "c1", "validator": "exact_text", "expected": "3"}
                    ]
                },
            },
        }

    def observations(self):
        gib = 1024**3
        return {
            "q1": {"output_text": "9", "first_output_byte_ms": 100, "peak_rss_bytes": 5 * gib},
            "q2": {"output_text": "ALLOW", "first_output_byte_ms": 300, "peak_rss_bytes": 6 * gib},
            "m1": {"output_text": "Ciao", "first_output_byte_ms": 200, "peak_rss_bytes": 4 * gib},
            "t1": {
                "output_text": '{"content":"OK","type":"final"}',
                "first_output_byte_ms": 400,
                "peak_rss_bytes": 7 * gib,
            },
            "c1": {"output_text": "3", "first_output_byte_ms": 500, "peak_rss_bytes": 3 * gib},
        }

    def test_scores_correctness_and_performance(self):
        metrics, results = evaluate_native_metrics(self.suite(), self.observations())
        self.assertEqual(metrics["quality_score"], 50.0)
        self.assertEqual(metrics["multilingual_semantic_score"], 100.0)
        self.assertEqual(metrics["tool_structured_reliability_pct"], 100.0)
        self.assertEqual(metrics["coding_score"], 100.0)
        self.assertEqual(metrics["peak_ram_gib"], 7.0)
        self.assertEqual(metrics["p50_first_token_ms"], 300.0)
        self.assertEqual(len(results), 5)
        self.assertFalse(next(result for result in results if result.case_id == "q2").passed)

    def test_missing_case_is_rejected(self):
        observations = self.observations()
        del observations["q1"]
        with self.assertRaisesRegex(ValueError, "missing observation"):
            evaluate_native_metrics(self.suite(), observations)

    def test_extra_case_is_rejected(self):
        observations = self.observations()
        observations["extra"] = {
            "output_text": "x",
            "first_output_byte_ms": 1,
            "peak_rss_bytes": 1,
        }
        with self.assertRaisesRegex(ValueError, "unexpected scoring observations"):
            evaluate_native_metrics(self.suite(), observations)

    def test_invalid_performance_evidence_is_rejected(self):
        observations = self.observations()
        observations["q1"]["first_output_byte_ms"] = -1
        with self.assertRaisesRegex(ValueError, "non-negative"):
            evaluate_native_metrics(self.suite(), observations)


if __name__ == "__main__":
    unittest.main()
