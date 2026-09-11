from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_PROVIDER_CONTRACT = "oyyo-native-provider-0.1"
_RECEIPT_TYPE = "oyyo-native-provider-evaluation-0.1"


@dataclass
class WorkflowValidation:
    workflow_id: str
    passed: bool
    reason: str | None


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _required_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _required_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _sha256(value: Any, label: str) -> str:
    text = _required_string(value, label).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{label} must be a SHA-256 digest")
    return text


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_workflow_output(
    workflow_id: str,
    output_text: str,
    spec: dict[str, Any],
) -> WorkflowValidation:
    kind = _required_string(spec.get("validator"), f"workflow {workflow_id} validator")
    text = output_text.strip()

    if kind == "exact_text":
        expected = _required_string(spec.get("expected"), f"workflow {workflow_id} expected")
        if text != expected:
            return WorkflowValidation(workflow_id, False, "generated text did not exactly match fixture")
        return WorkflowValidation(workflow_id, True, None)

    if kind == "accepted_texts":
        expected = spec.get("accepted")
        if not isinstance(expected, list) or not expected or not all(
            isinstance(item, str) and item.strip() for item in expected
        ):
            raise ValueError(f"workflow {workflow_id} accepted must be a non-empty string list")
        accepted = {item.strip() for item in expected}
        if text not in accepted:
            return WorkflowValidation(workflow_id, False, "generated text is outside accepted fixture outputs")
        return WorkflowValidation(workflow_id, True, None)

    if kind == "exact_json":
        expected = spec.get("expected")
        if not isinstance(expected, (dict, list)):
            raise ValueError(f"workflow {workflow_id} expected must be JSON object or array")
        try:
            actual = json.loads(text)
        except json.JSONDecodeError:
            return WorkflowValidation(workflow_id, False, "generated output is not valid JSON")
        if _canonical_json(actual) != _canonical_json(expected):
            return WorkflowValidation(workflow_id, False, "generated JSON did not exactly match fixture")
        return WorkflowValidation(workflow_id, True, None)

    raise ValueError(f"unsupported workflow validator: {kind}")


def _validate_receipt(
    receipt: dict[str, Any],
    expected_workflow: str,
    expected_suite_id: str,
    spec: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    if receipt.get("schema_version") != "0.1":
        raise ValueError("provider evaluation receipt schema_version must be 0.1")
    if receipt.get("receipt_type") != _RECEIPT_TYPE:
        raise ValueError(f"provider evaluation receipt_type must be {_RECEIPT_TYPE}")
    if receipt.get("evaluation_only") is not True:
        raise ValueError("provider evaluation receipt must be explicitly evaluation_only")
    if receipt.get("acknowledged_unqualified_evaluation") is not True:
        raise ValueError("provider evaluation must record explicit unqualified-evaluation acknowledgement")

    candidate = _required_dict(receipt.get("candidate"), "candidate")
    model_id = _required_string(candidate.get("model_id"), "candidate.model_id")
    artifact_sha256 = _sha256(candidate.get("artifact_sha256"), "candidate.artifact_sha256")
    package_sha256 = _sha256(
        candidate.get("package_manifest_sha256"), "candidate.package_manifest_sha256"
    )
    rights = _required_string(candidate.get("rights_review_status"), "candidate.rights_review_status")
    if rights == "rejected":
        raise ValueError("rejected-rights candidate cannot contribute native workflow evidence")

    provider = _required_dict(receipt.get("provider"), "provider")
    contract = _required_string(provider.get("provider_contract"), "provider.provider_contract")
    if contract != _PROVIDER_CONTRACT:
        raise ValueError(f"provider contract must be {_PROVIDER_CONTRACT}")

    workflow = _required_dict(receipt.get("workflow"), "workflow")
    workflow_id = _required_string(workflow.get("id"), "workflow.id")
    if workflow_id != expected_workflow:
        raise ValueError(
            f"provider receipt workflow {workflow_id} does not match expected {expected_workflow}"
        )

    suite_id = _required_string(workflow.get("suite_id"), "workflow.suite_id")
    if suite_id != expected_suite_id:
        raise ValueError(
            f"provider receipt suite {suite_id} does not match expected {expected_suite_id}"
        )

    expected_prompt = spec.get("prompt")
    if not isinstance(expected_prompt, str) or not expected_prompt:
        raise ValueError(f"workflow {workflow_id} prompt must be a non-empty string")
    expected_prompt_sha256 = _sha256_text(expected_prompt)
    observed_prompt_sha256 = _sha256(workflow.get("prompt_sha256"), "workflow.prompt_sha256")
    if observed_prompt_sha256 != expected_prompt_sha256:
        raise ValueError(
            f"workflow {workflow_id} prompt_sha256 does not match the frozen suite prompt"
        )

    expected_max_tokens = _required_positive_int(
        spec.get("max_tokens"), f"workflow {workflow_id} max_tokens"
    )
    observed_max_tokens = _required_positive_int(
        workflow.get("max_tokens"), "workflow.max_tokens"
    )
    if observed_max_tokens != expected_max_tokens:
        raise ValueError(
            f"workflow {workflow_id} max_tokens {observed_max_tokens} does not match frozen suite value {expected_max_tokens}"
        )

    if workflow.get("deployment") != "local":
        raise ValueError("native candidate workflow evidence must use local deployment")
    if _required_bool(
        workflow.get("native_provider_inference_passed"),
        "workflow.native_provider_inference_passed",
    ) is not True:
        raise ValueError(f"workflow {workflow_id} did not execute through the native provider")
    if _required_bool(
        workflow.get("policy_handoff_passed"), "workflow.policy_handoff_passed"
    ) is not True:
        raise ValueError(f"workflow {workflow_id} did not pass policy handoff")

    isolation = _required_dict(receipt.get("isolation"), "isolation")
    if isolation.get("external_model_fallback_enabled") is not False:
        raise ValueError("external model fallback must be explicitly disabled")
    requests = isolation.get("external_ai_requests_observed")
    if not isinstance(requests, int) or isinstance(requests, bool) or requests != 0:
        raise ValueError("external_ai_requests_observed must be exactly zero")
    providers = isolation.get("external_ai_providers")
    if not isinstance(providers, list) or providers:
        raise ValueError("external_ai_providers must be an explicitly empty list")

    output = _required_dict(receipt.get("output"), "output")
    output_text = _required_string(output.get("text"), "output.text")

    return model_id, artifact_sha256, package_sha256, contract, output_text


def assemble_independence_evidence(
    receipts_by_workflow: dict[str, dict[str, Any]],
    suite: dict[str, Any],
    *,
    candidate_id: str,
    family: str,
) -> tuple[dict[str, Any], list[WorkflowValidation]]:
    if suite.get("schema_version") != "0.1":
        raise ValueError("native workflow suite schema_version must be 0.1")
    suite_id = _required_string(suite.get("suite_id"), "suite.suite_id")
    suite_contract = _required_string(suite.get("provider_contract"), "suite.provider_contract")
    if suite_contract != _PROVIDER_CONTRACT:
        raise ValueError(f"suite provider_contract must be {_PROVIDER_CONTRACT}")
    specs = _required_dict(suite.get("workflows"), "suite.workflows")
    if not specs:
        raise ValueError("suite.workflows must not be empty")
    if set(receipts_by_workflow) != set(specs):
        missing = sorted(set(specs) - set(receipts_by_workflow))
        extra = sorted(set(receipts_by_workflow) - set(specs))
        raise ValueError(f"workflow receipt set mismatch; missing={missing}, extra={extra}")

    bound_model: str | None = None
    bound_artifact: str | None = None
    bound_package: str | None = None
    validations: list[WorkflowValidation] = []
    workflows: dict[str, Any] = {}

    for workflow_id, spec_value in specs.items():
        spec = _required_dict(spec_value, f"suite.workflows.{workflow_id}")
        model_id, artifact_sha256, package_sha256, contract, output_text = _validate_receipt(
            receipts_by_workflow[workflow_id], workflow_id, suite_id, spec
        )
        if bound_model is None:
            bound_model = model_id
            bound_artifact = artifact_sha256
            bound_package = package_sha256
        elif (
            model_id != bound_model
            or artifact_sha256 != bound_artifact
            or package_sha256 != bound_package
        ):
            raise ValueError("all workflow receipts must bind the same model, artifact and package")

        validation = validate_workflow_output(workflow_id, output_text, spec)
        validations.append(validation)
        workflows[workflow_id] = {
            "passed": validation.passed,
            "execution_mode": "native",
            "model_id": model_id,
            "provider_contract": contract,
            "external_ai_provider_used": False,
            "artifact_sha256": artifact_sha256,
            "suite_id": suite_id,
            "prompt_sha256": _sha256_text(spec["prompt"]),
            "max_tokens": spec["max_tokens"],
            "validation_reason": validation.reason,
        }

    assert bound_model is not None and bound_artifact is not None and bound_package is not None
    evidence = {
        "schema_version": "0.1",
        "candidate_id": _required_string(candidate_id, "candidate_id"),
        "model_id": bound_model,
        "family": _required_string(family, "family"),
        "artifact_sha256": bound_artifact,
        "package_manifest_sha256": bound_package,
        "suite_id": suite_id,
        "runtime": {
            "model_id": bound_model,
            "native_model_loaded": True,
            "external_model_fallback_enabled": False,
            "external_ai_requests_observed": 0,
            "external_ai_providers": [],
        },
        "workflows": workflows,
    }
    return evidence, validations
