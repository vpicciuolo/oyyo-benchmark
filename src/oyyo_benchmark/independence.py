from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class IndependenceEvaluation:
    candidate_id: str
    model_id: str
    family: str
    gate_id: str
    artifact_sha256: str
    passed: bool
    violations: list[str]
    required_workflows: list[str]
    passed_workflows: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_runtime_isolation(runtime: dict[str, Any], model_id: str) -> list[str]:
    violations: list[str] = []
    runtime_model_id = _required_string(runtime.get("model_id"), "runtime.model_id")
    if runtime_model_id != model_id:
        violations.append(
            f"runtime model id {runtime_model_id} does not match evidence model id {model_id}"
        )

    if runtime.get("native_model_loaded") is not True:
        violations.append("native model is not loaded")
    if runtime.get("external_model_fallback_enabled") is not False:
        violations.append("external model fallback is enabled or not explicitly disabled")

    requests = runtime.get("external_ai_requests_observed")
    if not isinstance(requests, int) or isinstance(requests, bool) or requests < 0:
        raise ValueError("runtime.external_ai_requests_observed must be a non-negative integer")
    if requests != 0:
        violations.append(f"{requests} external AI request(s) were observed")

    providers = runtime.get("external_ai_providers")
    if not isinstance(providers, list):
        raise ValueError("runtime.external_ai_providers must be a list")
    seen: set[str] = set()
    for index, provider in enumerate(providers):
        if not isinstance(provider, dict):
            raise ValueError(f"runtime.external_ai_providers[{index}] must be an object")
        provider_id = _required_string(
            provider.get("provider_id"),
            f"runtime.external_ai_providers[{index}].provider_id",
        )
        if provider_id in seen:
            raise ValueError("runtime external AI provider ids must be unique")
        seen.add(provider_id)
        enabled = provider.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError(
                f"runtime.external_ai_providers[{index}].enabled must be boolean"
            )
        if enabled:
            violations.append(f"external AI provider {provider_id} is enabled")
    return violations


def evaluate_independence(
    evidence: dict[str, Any], matrix: dict[str, Any]
) -> IndependenceEvaluation:
    if evidence.get("schema_version") != "0.1":
        raise ValueError("independence evidence schema_version must be 0.1")

    candidate_id = _required_string(evidence.get("candidate_id"), "candidate_id")
    model_id = _required_string(evidence.get("model_id"), "model_id")
    if not model_id.startswith("oyyo-"):
        raise ValueError("model_id must identify an OYYO native model")
    family = _required_string(evidence.get("family"), "family")
    artifact_sha256 = _required_string(
        evidence.get("artifact_sha256"), "artifact_sha256"
    )
    if not _SHA256.fullmatch(artifact_sha256):
        raise ValueError(
            "artifact_sha256 must be a 64-character hexadecimal SHA-256 digest"
        )

    config = matrix.get("independence")
    if not isinstance(config, dict):
        raise ValueError("matrix.independence configuration is required")
    gate_id = _required_string(config.get("gate_id"), "matrix.independence.gate_id")
    expected_provider_contract = _required_string(
        config.get("provider_contract"), "matrix.independence.provider_contract"
    )
    workflows_by_family = config.get("required_workflows_by_family")
    if not isinstance(workflows_by_family, dict):
        raise ValueError("matrix.independence.required_workflows_by_family is required")
    required = workflows_by_family.get(family)
    if not isinstance(required, list) or not required:
        raise ValueError(f"no independence workflow set is configured for family {family}")
    required_workflows = [_required_string(item, "required workflow") for item in required]
    if len(set(required_workflows)) != len(required_workflows):
        raise ValueError("required independence workflows must be unique")

    runtime = evidence.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("runtime independence evidence is required")
    violations = _validate_runtime_isolation(runtime, model_id)

    workflows = evidence.get("workflows")
    if not isinstance(workflows, dict):
        raise ValueError("workflows must be an object")
    passed_workflows: list[str] = []
    for workflow_id in required_workflows:
        workflow = workflows.get(workflow_id)
        if not isinstance(workflow, dict):
            violations.append(f"required workflow {workflow_id} has no evidence")
            continue
        if workflow.get("passed") is not True:
            violations.append(f"required workflow {workflow_id} did not pass")
            continue
        if workflow.get("execution_mode") != "native":
            violations.append(f"required workflow {workflow_id} was not executed natively")
            continue
        if workflow.get("model_id") != model_id:
            violations.append(f"required workflow {workflow_id} used a different model id")
            continue
        if workflow.get("provider_contract") != expected_provider_contract:
            violations.append(
                f"required workflow {workflow_id} used a different provider contract"
            )
            continue
        if workflow.get("external_ai_provider_used") is not False:
            violations.append(
                f"required workflow {workflow_id} used or did not explicitly exclude an external AI provider"
            )
            continue
        if workflow.get("artifact_sha256") != artifact_sha256:
            violations.append(f"required workflow {workflow_id} used a different artifact")
            continue
        passed_workflows.append(workflow_id)

    return IndependenceEvaluation(
        candidate_id=candidate_id,
        model_id=model_id,
        family=family,
        gate_id=gate_id,
        artifact_sha256=artifact_sha256.lower(),
        passed=not violations,
        violations=violations,
        required_workflows=required_workflows,
        passed_workflows=passed_workflows,
    )
