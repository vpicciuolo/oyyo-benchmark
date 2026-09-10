import copy
import unittest

from oyyo_benchmark.candidates import evaluate_candidate
from oyyo_benchmark.independence import evaluate_independence


MATRIX = {
    "hard_gates": [
        {"id": "runtime_loadable"},
        {"id": "independence_test_passed"},
    ],
    "independence": {
        "gate_id": "oyyo-native-independence-0.1",
        "provider_contract": "oyyo-native-provider-0.1",
        "required_workflows_by_family": {
            "mini": ["chat", "structured_output", "tool_calling", "translation"]
        },
    },
    "family_profiles": {
        "mini": {
            "metrics": [
                {
                    "id": "quality",
                    "direction": "higher_is_better",
                    "min": 0,
                    "max": 100,
                    "weight": 1.0,
                }
            ]
        }
    },
}


def evidence():
    model_id = "oyyo-mini-test"
    package_sha256 = "aa" * 32
    workflow = {
        "passed": True,
        "execution_mode": "native",
        "model_id": model_id,
        "provider_contract": "oyyo-native-provider-0.1",
        "external_ai_provider_used": False,
        "package_sha256": package_sha256,
    }
    return {
        "schema_version": "0.1",
        "candidate_id": "candidate-mini",
        "model_id": model_id,
        "family": "mini",
        "package_sha256": package_sha256,
        "runtime": {
            "model_id": model_id,
            "native_model_loaded": True,
            "external_model_fallback_enabled": False,
            "external_ai_requests_observed": 0,
            "external_ai_providers": [
                {"provider_id": "openai", "enabled": False},
                {"provider_id": "anthropic", "enabled": False},
            ],
        },
        "workflows": {
            "chat": copy.deepcopy(workflow),
            "structured_output": copy.deepcopy(workflow),
            "tool_calling": copy.deepcopy(workflow),
            "translation": copy.deepcopy(workflow),
        },
    }


class IndependenceEvaluationTest(unittest.TestCase):
    def test_valid_native_evidence_passes(self):
        result = evaluate_independence(evidence(), MATRIX)
        self.assertTrue(result.passed)
        self.assertEqual(result.violations, [])
        self.assertEqual(
            result.passed_workflows,
            ["chat", "structured_output", "tool_calling", "translation"],
        )

    def test_enabled_external_provider_fails(self):
        data = evidence()
        data["runtime"]["external_ai_providers"][0]["enabled"] = True
        result = evaluate_independence(data, MATRIX)
        self.assertFalse(result.passed)
        self.assertTrue(any("openai" in violation for violation in result.violations))

    def test_observed_external_request_fails(self):
        data = evidence()
        data["runtime"]["external_ai_requests_observed"] = 1
        result = evaluate_independence(data, MATRIX)
        self.assertFalse(result.passed)
        self.assertTrue(any("external AI request" in item for item in result.violations))

    def test_missing_required_workflow_fails(self):
        data = evidence()
        del data["workflows"]["tool_calling"]
        result = evaluate_independence(data, MATRIX)
        self.assertFalse(result.passed)
        self.assertTrue(any("tool_calling" in item for item in result.violations))

    def test_wrong_provider_contract_fails(self):
        data = evidence()
        data["workflows"]["translation"]["provider_contract"] = "other-provider"
        result = evaluate_independence(data, MATRIX)
        self.assertFalse(result.passed)
        self.assertTrue(any("provider contract" in item for item in result.violations))

    def test_candidate_self_assertion_cannot_bypass_verified_gate(self):
        candidate = {
            "candidate_id": "candidate-mini",
            "family": "mini",
            "hard_gates": {
                "runtime_loadable": True,
                "independence_test_passed": True,
            },
            "metrics": {"quality": 80},
        }
        forged = evaluate_candidate(candidate, MATRIX)
        self.assertFalse(forged.eligible)
        self.assertEqual(forged.hard_gate_failures, ["independence_test_passed"])

        independence = evaluate_independence(evidence(), MATRIX)
        verified = evaluate_candidate(
            candidate,
            MATRIX,
            {"independence_test_passed": independence.passed},
        )
        self.assertTrue(verified.eligible)

    def test_package_identity_mismatch_fails_workflow(self):
        data = evidence()
        data["workflows"]["chat"]["package_sha256"] = "bb" * 32
        result = evaluate_independence(data, MATRIX)
        self.assertFalse(result.passed)
        self.assertTrue(any("different package" in item for item in result.violations))


if __name__ == "__main__":
    unittest.main()
