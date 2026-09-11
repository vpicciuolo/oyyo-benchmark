from __future__ import annotations

import hashlib
import unittest

from oyyo_benchmark.independence import evaluate_independence
from oyyo_benchmark.native_evidence import (
    assemble_independence_evidence,
    validate_workflow_output,
)


ARTIFACT = "11" * 32
PACKAGE = "22" * 32
MODEL = "oyyo-mini-dev-test"
CANDIDATE = "oyyo-mini-test-r1"
SUITE_ID = "oyyo-mini-native-independence-workflows-0.1"


def suite() -> dict:
    return {
        "schema_version": "0.1",
        "suite_id": SUITE_ID,
        "provider_contract": "oyyo-native-provider-0.1",
        "workflows": {
            "chat": {
                "prompt": "/no_think\nReturn exactly this text and nothing else: OYYO_CHAT_OK",
                "validator": "exact_text",
                "expected": "OYYO_CHAT_OK",
                "max_tokens": 64,
            },
            "structured_output": {
                "prompt": "/no_think\nReturn exactly this JSON object and nothing else: {\"status\":\"OYYO_STRUCTURED_OK\",\"count\":2}",
                "validator": "exact_json",
                "expected": {"status": "OYYO_STRUCTURED_OK", "count": 2},
                "max_tokens": 96,
            },
            "tool_calling": {
                "prompt": "/no_think\nReturn exactly one JSON object and nothing else.",
                "validator": "exact_json",
                "expected": {
                    "type": "tool_call",
                    "installation_id": "fixture-read",
                    "tool": "lookup",
                    "arguments": {"query": "OYYO"},
                },
                "max_tokens": 128,
            },
            "translation": {
                "prompt": "/no_think\nTranslate the English sentence 'The storage node is online.' into Italian. Return only the translation and nothing else.",
                "validator": "accepted_texts",
                "accepted": ["Il nodo di archiviazione è online."],
                "max_tokens": 64,
            },
        },
    }


def output_for(workflow: str) -> str:
    return {
        "chat": "OYYO_CHAT_OK",
        "structured_output": '{"count":2,"status":"OYYO_STRUCTURED_OK"}',
        "tool_calling": '{"arguments":{"query":"OYYO"},"tool":"lookup","installation_id":"fixture-read","type":"tool_call"}',
        "translation": "Il nodo di archiviazione è online.",
    }[workflow]


def prompt_sha256(workflow: str) -> str:
    prompt = suite()["workflows"][workflow]["prompt"]
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def receipt(workflow: str) -> dict:
    spec = suite()["workflows"][workflow]
    return {
        "schema_version": "0.1",
        "receipt_type": "oyyo-native-provider-evaluation-0.1",
        "evaluation_only": True,
        "acknowledged_unqualified_evaluation": True,
        "candidate": {
            "model_id": MODEL,
            "artifact_sha256": ARTIFACT,
            "artifact_size_bytes": 1234,
            "quantization": "Q4_K_M",
            "package_manifest_sha256": PACKAGE,
            "rights_review_status": "pending",
            "benchmark_status": "candidate",
            "qualification_id": None,
        },
        "provider": {
            "provider_id": "oyyo-native-eval",
            "provider_contract": "oyyo-native-provider-0.1",
            "backend": "llama_cpp",
            "llama_binary_sha256": "33" * 32,
        },
        "hardware": {
            "arch": "x86_64",
            "memory_bytes": 16 * 1024**3,
            "verified_backends": [],
            "compatible_profile_ids": ["cpu"],
        },
        "workflow": {
            "id": workflow,
            "suite_id": SUITE_ID,
            "prompt_sha256": prompt_sha256(workflow),
            "max_tokens": spec["max_tokens"],
            "evaluation_threads": 2,
            "deployment": "local",
            "policy_profile_id": "oyyo-local-runtime-default",
            "policy_profile_revision": "0.1",
            "tool_action_mode": "disabled",
            "network_mode": "offline",
            "required": {},
            "policy_handoff_passed": True,
            "native_provider_inference_passed": True,
        },
        "isolation": {
            "external_model_fallback_enabled": False,
            "external_ai_providers": [],
            "external_ai_requests_observed": 0,
        },
        "output": {
            "text": output_for(workflow),
            "backend": "llamacpp",
            "backend_version": "test",
        },
    }


def receipts() -> dict[str, dict]:
    return {workflow: receipt(workflow) for workflow in suite()["workflows"]}


def matrix() -> dict:
    return {
        "independence": {
            "gate_id": "oyyo-native-independence-0.1",
            "provider_contract": "oyyo-native-provider-0.1",
            "required_workflows_by_family": {
                "mini": ["chat", "structured_output", "tool_calling", "translation"]
            },
        }
    }


class NativeEvidenceTest(unittest.TestCase):
    def test_workflow_validators_are_deterministic(self):
        self.assertTrue(
            validate_workflow_output(
                "chat", "OYYO_CHAT_OK\n", {"validator": "exact_text", "expected": "OYYO_CHAT_OK"}
            ).passed
        )
        self.assertTrue(
            validate_workflow_output(
                "json", '{"b":2,"a":1}', {"validator": "exact_json", "expected": {"a": 1, "b": 2}}
            ).passed
        )
        self.assertFalse(
            validate_workflow_output(
                "chat", "OYYO_CHAT_OK extra", {"validator": "exact_text", "expected": "OYYO_CHAT_OK"}
            ).passed
        )

    def test_complete_receipts_assemble_and_pass_existing_independence_gate(self):
        evidence, validations = assemble_independence_evidence(
            receipts(), suite(), candidate_id=CANDIDATE, family="mini"
        )
        self.assertTrue(all(item.passed for item in validations))
        self.assertEqual(evidence["suite_id"], SUITE_ID)
        result = evaluate_independence(evidence, matrix())
        self.assertTrue(result.passed)
        self.assertEqual(result.artifact_sha256, ARTIFACT)
        self.assertEqual(set(result.passed_workflows), set(suite()["workflows"]))

    def test_workflow_receipts_must_bind_same_artifact(self):
        values = receipts()
        values["translation"]["candidate"]["artifact_sha256"] = "44" * 32
        with self.assertRaisesRegex(ValueError, "same model, artifact and package"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_receipt_must_bind_frozen_suite_id(self):
        values = receipts()
        values["chat"]["workflow"]["suite_id"] = "wrong-suite"
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_receipt_must_bind_exact_frozen_prompt(self):
        values = receipts()
        values["chat"]["workflow"]["prompt_sha256"] = hashlib.sha256(
            b"different prompt"
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "prompt_sha256"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_receipt_must_bind_exact_token_budget(self):
        values = receipts()
        values["structured_output"]["workflow"]["max_tokens"] = 97
        with self.assertRaisesRegex(ValueError, "max_tokens"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_external_provider_activity_is_rejected(self):
        values = receipts()
        values["chat"]["isolation"]["external_ai_requests_observed"] = 1
        with self.assertRaisesRegex(ValueError, "exactly zero"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_external_provider_inventory_must_be_empty(self):
        values = receipts()
        values["chat"]["isolation"]["external_ai_providers"] = [
            {"provider_id": "external", "enabled": False}
        ]
        with self.assertRaisesRegex(ValueError, "explicitly empty"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_failed_output_validation_does_not_pass_independence(self):
        values = receipts()
        values["structured_output"]["output"]["text"] = '{"status":"wrong","count":2}'
        evidence, validations = assemble_independence_evidence(
            values, suite(), candidate_id=CANDIDATE, family="mini"
        )
        self.assertFalse(next(item for item in validations if item.workflow_id == "structured_output").passed)
        result = evaluate_independence(evidence, matrix())
        self.assertFalse(result.passed)
        self.assertIn("required workflow structured_output did not pass", result.violations)

    def test_missing_or_extra_receipt_is_rejected(self):
        values = receipts()
        del values["translation"]
        with self.assertRaisesRegex(ValueError, "receipt set mismatch"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")

    def test_rejected_rights_receipt_is_rejected(self):
        values = receipts()
        values["chat"]["candidate"]["rights_review_status"] = "rejected"
        with self.assertRaisesRegex(ValueError, "rejected-rights"):
            assemble_independence_evidence(values, suite(), candidate_id=CANDIDATE, family="mini")


if __name__ == "__main__":
    unittest.main()