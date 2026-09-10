import copy
import unittest

from oyyo_benchmark.qualification import qualify_candidate


MATRIX = {
    "matrix_id": "matrix-test-0.1",
    "hard_gates": [
        {"id": "runtime_loadable"},
        {"id": "independence_test_passed"},
    ],
    "independence": {
        "gate_id": "oyyo-native-independence-0.1",
        "provider_contract": "oyyo-native-provider-0.1",
        "required_workflows_by_family": {"mini": ["chat"]},
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


def candidate():
    return {
        "candidate_id": "candidate-mini",
        "family": "mini",
        "hard_gates": {
            "runtime_loadable": True,
            "independence_test_passed": True,
        },
        "metrics": {"quality": 80},
    }


def independence():
    model_id = "oyyo-mini-test"
    artifact_sha256 = "aa" * 32
    return {
        "schema_version": "0.1",
        "candidate_id": "candidate-mini",
        "model_id": model_id,
        "family": "mini",
        "artifact_sha256": artifact_sha256,
        "runtime": {
            "model_id": model_id,
            "native_model_loaded": True,
            "external_model_fallback_enabled": False,
            "external_ai_requests_observed": 0,
            "external_ai_providers": [],
        },
        "workflows": {
            "chat": {
                "passed": True,
                "execution_mode": "native",
                "model_id": model_id,
                "provider_contract": "oyyo-native-provider-0.1",
                "external_ai_provider_used": False,
                "artifact_sha256": artifact_sha256,
            }
        },
    }


class NativeQualificationTest(unittest.TestCase):
    def test_qualified_record_is_deterministic(self):
        first = qualify_candidate(candidate(), independence(), MATRIX)
        second = qualify_candidate(candidate(), independence(), MATRIX)
        self.assertTrue(first.qualified)
        self.assertEqual(first.qualification_id, second.qualification_id)
        self.assertEqual(first.evidence_sha256, second.evidence_sha256)
        self.assertEqual(first.artifact_sha256, "aa" * 32)

    def test_changed_evidence_changes_qualification_identity(self):
        first = qualify_candidate(candidate(), independence(), MATRIX)
        changed = candidate()
        changed["metrics"]["quality"] = 81
        second = qualify_candidate(changed, independence(), MATRIX)
        self.assertNotEqual(first.qualification_id, second.qualification_id)
        self.assertNotEqual(first.evidence_sha256, second.evidence_sha256)

    def test_failed_independence_cannot_qualify(self):
        evidence = independence()
        evidence["runtime"]["external_model_fallback_enabled"] = True
        result = qualify_candidate(candidate(), evidence, MATRIX)
        self.assertFalse(result.qualified)
        self.assertFalse(result.independence_passed)
        self.assertIn("independence_test_passed", result.hard_gate_failures)

    def test_candidate_identity_mismatch_is_rejected(self):
        data = copy.deepcopy(independence())
        data["candidate_id"] = "other-candidate"
        with self.assertRaises(ValueError):
            qualify_candidate(candidate(), data, MATRIX)


if __name__ == "__main__":
    unittest.main()
