import copy
import hashlib
import json
from pathlib import Path
import unittest

from oyyo_benchmark.qualification import (
    NATIVE_FIRST_CANDIDATE_MATRIX_ID,
    QUALIFICATION_SCHEMA_VERSION,
    qualify_candidate,
    validate_native_first_candidate_matrix,
    verify_qualification_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX = json.loads(
    (ROOT / "suites" / "native-first-candidate-0.1.json").read_text(encoding="utf-8")
)
HARD_GATES = [gate["id"] for gate in MATRIX["hard_gates"]]


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def candidate():
    return {
        "candidate_id": "candidate-mini",
        "family": "mini",
        "package_target": {
            "model_id": "oyyo-mini-test",
            "provider_contract": "oyyo-native-provider-0.1",
            "primary_artifact_sha256": "aa" * 32,
        },
        "hard_gates": {gate: True for gate in HARD_GATES},
        "metrics": {
            "quality_score": 72,
            "multilingual_semantic_score": 75,
            "tool_structured_reliability_pct": 92,
            "coding_score": 68,
            "peak_ram_gib": 7.5,
            "p50_first_token_ms": 420,
        },
    }


def independence():
    model_id = "oyyo-mini-test"
    artifact_sha256 = "aa" * 32
    workflows = {}
    for workflow_id in MATRIX["independence"]["required_workflows_by_family"]["mini"]:
        workflows[workflow_id] = {
            "passed": True,
            "execution_mode": "native",
            "model_id": model_id,
            "provider_contract": "oyyo-native-provider-0.1",
            "external_ai_provider_used": False,
            "artifact_sha256": artifact_sha256,
        }
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
        "workflows": workflows,
    }


class NativeQualificationTest(unittest.TestCase):
    def test_frozen_matrix_fixture_matches_runtime_contract(self):
        validate_native_first_candidate_matrix(MATRIX)
        self.assertEqual(MATRIX["matrix_id"], NATIVE_FIRST_CANDIDATE_MATRIX_ID)
        self.assertEqual(len(HARD_GATES), 10)

    def test_qualified_record_is_deterministic_and_self_verifying(self):
        first = qualify_candidate(candidate(), independence(), MATRIX)
        second = qualify_candidate(candidate(), independence(), MATRIX)
        self.assertTrue(first.qualified)
        self.assertEqual(first.schema_version, QUALIFICATION_SCHEMA_VERSION)
        self.assertEqual(first.qualification_id, second.qualification_id)
        self.assertEqual(first.evidence_sha256, second.evidence_sha256)
        self.assertEqual(first.artifact_sha256, "aa" * 32)
        self.assertEqual(first.provider_contract, "oyyo-native-provider-0.1")
        self.assertEqual(first.evidence_sha256, canonical_sha256(first.evidence_binding))
        self.assertEqual(first.matrix_sha256, canonical_sha256(MATRIX))
        self.assertEqual(first.candidate_sha256, canonical_sha256(candidate()))
        self.assertEqual(
            first.independence_evidence_sha256,
            canonical_sha256(independence()),
        )
        self.assertEqual(
            first.evidence_binding["matrix"]["matrix_id"],
            NATIVE_FIRST_CANDIDATE_MATRIX_ID,
        )
        verify_qualification_receipt(first.to_dict())

    def test_changed_candidate_evidence_changes_qualification_identity(self):
        first = qualify_candidate(candidate(), independence(), MATRIX)
        changed = candidate()
        changed["metrics"]["quality_score"] = 81
        second = qualify_candidate(changed, independence(), MATRIX)
        self.assertNotEqual(first.qualification_id, second.qualification_id)
        self.assertNotEqual(first.evidence_sha256, second.evidence_sha256)

    def test_changed_nonsemantic_matrix_metadata_changes_receipt_identity(self):
        first = qualify_candidate(candidate(), independence(), MATRIX)
        changed = copy.deepcopy(MATRIX)
        changed["purpose"] = changed["purpose"] + " Test metadata change."
        second = qualify_candidate(candidate(), independence(), changed)
        self.assertEqual(first.matrix_id, second.matrix_id)
        self.assertNotEqual(first.matrix_sha256, second.matrix_sha256)
        self.assertNotEqual(first.qualification_id, second.qualification_id)

    def test_same_id_cannot_weaken_frozen_matrix_semantics(self):
        changed = copy.deepcopy(MATRIX)
        changed["family_profiles"]["mini"]["metrics"][0]["weight"] = 0.5
        with self.assertRaisesRegex(ValueError, "frozen mini metric semantics changed"):
            qualify_candidate(candidate(), independence(), changed)

        changed = copy.deepcopy(MATRIX)
        changed["hard_gates"] = changed["hard_gates"][-2:]
        with self.assertRaisesRegex(ValueError, "hard-gate semantics changed"):
            qualify_candidate(candidate(), independence(), changed)

    def test_receipt_binding_is_detached_from_mutable_inputs(self):
        candidate_value = candidate()
        independence_value = independence()
        matrix_value = copy.deepcopy(MATRIX)
        result = qualify_candidate(candidate_value, independence_value, matrix_value)
        digest = result.evidence_sha256

        candidate_value["metrics"]["quality_score"] = 1
        independence_value["runtime"]["external_ai_requests_observed"] = 99
        matrix_value["purpose"] = "mutated"

        self.assertEqual(result.evidence_sha256, digest)
        self.assertEqual(result.evidence_sha256, canonical_sha256(result.evidence_binding))
        self.assertEqual(
            result.evidence_binding["candidate"]["metrics"]["quality_score"], 72
        )
        self.assertEqual(
            result.evidence_binding["matrix"]["matrix_id"],
            NATIVE_FIRST_CANDIDATE_MATRIX_ID,
        )
        verify_qualification_receipt(result.to_dict())

    def test_tampered_embedded_candidate_is_rejected(self):
        receipt = qualify_candidate(candidate(), independence(), MATRIX).to_dict()
        receipt["evidence_binding"]["candidate"]["metrics"]["quality_score"] = 99
        with self.assertRaises(ValueError):
            verify_qualification_receipt(receipt)

    def test_forged_summary_identity_is_rejected(self):
        receipt = qualify_candidate(candidate(), independence(), MATRIX).to_dict()
        receipt["artifact_sha256"] = "bb" * 32
        with self.assertRaises(ValueError):
            verify_qualification_receipt(receipt)

    def test_forged_qualification_id_is_rejected(self):
        receipt = qualify_candidate(candidate(), independence(), MATRIX).to_dict()
        receipt["qualification_id"] = "oyyo-qualification-forged"
        with self.assertRaises(ValueError):
            verify_qualification_receipt(receipt)

    def test_rehashed_forged_qualified_flag_is_rejected_by_recomputation(self):
        bad_candidate = candidate()
        bad_candidate["hard_gates"]["runtime_loadable"] = False
        receipt = qualify_candidate(bad_candidate, independence(), MATRIX).to_dict()
        self.assertFalse(receipt["qualified"])
        receipt["qualified"] = True
        receipt["hard_gate_failures"] = []
        receipt["score"] = 100.0
        with self.assertRaisesRegex(ValueError, "recomputed qualification evidence"):
            verify_qualification_receipt(receipt)

    def test_failed_independence_cannot_qualify(self):
        evidence = independence()
        evidence["runtime"]["external_model_fallback_enabled"] = True
        result = qualify_candidate(candidate(), evidence, MATRIX)
        self.assertFalse(result.qualified)
        self.assertFalse(result.independence_passed)
        self.assertIn("independence_test_passed", result.hard_gate_failures)
        verify_qualification_receipt(result.to_dict())

    def test_candidate_identity_mismatch_is_rejected(self):
        data = copy.deepcopy(independence())
        data["candidate_id"] = "other-candidate"
        with self.assertRaises(ValueError):
            qualify_candidate(candidate(), data, MATRIX)

    def test_candidate_model_binding_mismatch_is_rejected(self):
        value = candidate()
        value["package_target"]["model_id"] = "oyyo-mini-other"
        with self.assertRaisesRegex(ValueError, "model_id"):
            qualify_candidate(value, independence(), MATRIX)

    def test_candidate_artifact_binding_mismatch_is_rejected(self):
        value = candidate()
        value["package_target"]["primary_artifact_sha256"] = "bb" * 32
        with self.assertRaisesRegex(ValueError, "primary artifact"):
            qualify_candidate(value, independence(), MATRIX)

    def test_candidate_provider_contract_mismatch_is_rejected(self):
        value = candidate()
        value["package_target"]["provider_contract"] = "other-provider"
        with self.assertRaisesRegex(ValueError, "provider contract"):
            qualify_candidate(value, independence(), MATRIX)


if __name__ == "__main__":
    unittest.main()
