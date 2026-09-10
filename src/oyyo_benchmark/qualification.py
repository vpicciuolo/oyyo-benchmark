from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

from .candidates import evaluate_candidate
from .independence import evaluate_independence


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
QUALIFICATION_SCHEMA_VERSION = "0.2"
QUALIFICATION_ID_PREFIX = "oyyo-qualification-"
NATIVE_FIRST_CANDIDATE_MATRIX_ID = "oyyo-native-first-candidate-0.1"
NATIVE_PROVIDER_CONTRACT = "oyyo-native-provider-0.1"
INDEPENDENCE_GATE_ID = "oyyo-native-independence-0.1"

HARD_GATES = [
    "provenance_accepted",
    "commercial_use_allowed",
    "adaptation_rights_allowed",
    "reproducible_revision",
    "artifact_integrity_verified",
    "runtime_loadable",
    "policy_handoff_passed",
    "structured_tool_contract_passed",
    "benchmark_contamination_reviewed",
    "independence_test_passed",
]

EXPECTED_WORKFLOWS = {
    "mini": ["chat", "structured_output", "tool_calling", "translation"],
    "nano": ["chat", "structured_output", "translation"],
}

EXPECTED_METRICS = {
    "mini": [
        ("quality_score", "higher_is_better", 0.0, 100.0, 0.25),
        ("multilingual_semantic_score", "higher_is_better", 0.0, 100.0, 0.15),
        ("tool_structured_reliability_pct", "higher_is_better", 0.0, 100.0, 0.20),
        ("coding_score", "higher_is_better", 0.0, 100.0, 0.10),
        ("peak_ram_gib", "lower_is_better", 4.0, 16.0, 0.15),
        ("p50_first_token_ms", "lower_is_better", 50.0, 1500.0, 0.15),
    ],
    "nano": [
        ("quality_score", "higher_is_better", 0.0, 100.0, 0.20),
        ("multilingual_semantic_score", "higher_is_better", 0.0, 100.0, 0.10),
        ("tool_structured_reliability_pct", "higher_is_better", 0.0, 100.0, 0.10),
        ("peak_ram_gib", "lower_is_better", 1.0, 8.0, 0.30),
        ("p50_first_token_ms", "lower_is_better", 25.0, 1000.0, 0.20),
        ("package_size_gib", "lower_is_better", 0.25, 4.0, 0.10),
    ],
}


@dataclass
class NativeQualification:
    schema_version: str
    qualification_id: str
    matrix_id: str
    matrix_sha256: str
    candidate_id: str
    candidate_sha256: str
    model_id: str
    family: str
    artifact_sha256: str
    provider_contract: str
    qualified: bool
    score: float | None
    hard_gate_failures: list[str]
    missing_metrics: list[str]
    independence_gate_id: str
    independence_passed: bool
    independence_evidence_sha256: str
    evidence_binding: dict[str, Any]
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _frozen_json(value: Any) -> Any:
    """Detach qualification evidence from caller-owned mutable objects."""
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _required_sha256(value: Any, label: str) -> str:
    digest = _required_string(value, label).lower()
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def validate_native_first_candidate_matrix(matrix: dict[str, Any]) -> None:
    """Fail closed if qualification semantics drift under the frozen matrix id."""
    if matrix.get("schema_version") != "0.1":
        raise ValueError("native qualification matrix schema_version must be 0.1")
    if matrix.get("matrix_id") != NATIVE_FIRST_CANDIDATE_MATRIX_ID:
        raise ValueError(
            f"qualification only accepts frozen matrix {NATIVE_FIRST_CANDIDATE_MATRIX_ID}"
        )

    hard_gates = matrix.get("hard_gates")
    if not isinstance(hard_gates, list):
        raise ValueError("matrix.hard_gates must be an array")
    gate_ids = [
        gate.get("id") if isinstance(gate, dict) else None
        for gate in hard_gates
    ]
    if gate_ids != HARD_GATES:
        raise ValueError("frozen native qualification hard-gate semantics changed")

    independence = matrix.get("independence")
    if not isinstance(independence, dict):
        raise ValueError("matrix.independence must be an object")
    if independence.get("gate_id") != INDEPENDENCE_GATE_ID:
        raise ValueError("frozen independence gate id changed")
    if independence.get("provider_contract") != NATIVE_PROVIDER_CONTRACT:
        raise ValueError("frozen native provider contract changed")
    workflows = independence.get("required_workflows_by_family")
    if workflows != EXPECTED_WORKFLOWS:
        raise ValueError("frozen native independence workflow semantics changed")

    profiles = matrix.get("family_profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(EXPECTED_METRICS):
        raise ValueError("frozen native qualification family profiles changed")
    for family, expected in EXPECTED_METRICS.items():
        profile = profiles.get(family)
        if not isinstance(profile, dict):
            raise ValueError(f"matrix family profile {family} must be an object")
        metrics = profile.get("metrics")
        if not isinstance(metrics, list) or len(metrics) != len(expected):
            raise ValueError(f"frozen {family} metric set changed")
        observed = []
        for spec in metrics:
            if not isinstance(spec, dict):
                raise ValueError(f"matrix {family} metric must be an object")
            observed.append(
                (
                    spec.get("id"),
                    spec.get("direction"),
                    float(spec.get("min")),
                    float(spec.get("max")),
                    float(spec.get("weight")),
                )
            )
        if observed != expected:
            raise ValueError(f"frozen {family} metric semantics changed")


def _candidate_package_binding(candidate: dict[str, Any]) -> tuple[str, str, str]:
    package = candidate.get("package_target")
    if not isinstance(package, dict):
        raise ValueError("candidate.package_target is required for qualification")
    model_id = _required_string(package.get("model_id"), "candidate.package_target.model_id")
    artifact_sha256 = _required_sha256(
        package.get("primary_artifact_sha256"),
        "candidate.package_target.primary_artifact_sha256",
    )
    provider_contract = _required_string(
        package.get("provider_contract"),
        "candidate.package_target.provider_contract",
    )
    return model_id, artifact_sha256, provider_contract


def _matrix_provider_contract(matrix: dict[str, Any]) -> str:
    independence = matrix.get("independence")
    if not isinstance(independence, dict):
        raise ValueError("matrix.independence configuration is required")
    return _required_string(
        independence.get("provider_contract"),
        "matrix.independence.provider_contract",
    )


def _recompute(
    *,
    candidate: dict[str, Any],
    independence_evidence: dict[str, Any],
    matrix: dict[str, Any],
):
    validate_native_first_candidate_matrix(matrix)
    independence = evaluate_independence(independence_evidence, matrix)
    candidate_id = _required_string(candidate.get("candidate_id"), "candidate_id")
    family = _required_string(candidate.get("family"), "family")
    if candidate_id != independence.candidate_id:
        raise ValueError("candidate_id does not match the validated independence evidence")
    if family != independence.family:
        raise ValueError("candidate family does not match the independence evidence")

    package_model_id, package_artifact_sha256, package_provider_contract = (
        _candidate_package_binding(candidate)
    )
    matrix_provider_contract = _matrix_provider_contract(matrix)
    if package_model_id != independence.model_id:
        raise ValueError("candidate package model_id does not match independence evidence")
    if package_artifact_sha256 != independence.artifact_sha256:
        raise ValueError("candidate primary artifact does not match independence evidence")
    if package_provider_contract != matrix_provider_contract:
        raise ValueError("candidate provider contract does not match benchmark matrix")

    evaluation = evaluate_candidate(
        candidate,
        matrix,
        {"independence_test_passed": independence.passed},
    )
    matrix_id = _required_string(matrix.get("matrix_id"), "matrix_id")
    return (
        matrix_id,
        matrix_provider_contract,
        independence,
        evaluation,
        candidate_id,
        family,
    )


def verify_qualification_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("schema_version") != QUALIFICATION_SCHEMA_VERSION:
        raise ValueError(
            f"qualification schema_version must be {QUALIFICATION_SCHEMA_VERSION}"
        )

    binding = receipt.get("evidence_binding")
    if not isinstance(binding, dict):
        raise ValueError("evidence_binding must be an object")
    if binding.get("schema_version") != QUALIFICATION_SCHEMA_VERSION:
        raise ValueError(
            f"evidence_binding schema_version must be {QUALIFICATION_SCHEMA_VERSION}"
        )

    matrix = binding.get("matrix")
    candidate = binding.get("candidate")
    independence_evidence = binding.get("independence_evidence")
    if not isinstance(matrix, dict):
        raise ValueError("evidence_binding.matrix must be an object")
    if not isinstance(candidate, dict):
        raise ValueError("evidence_binding.candidate must be an object")
    if not isinstance(independence_evidence, dict):
        raise ValueError("evidence_binding.independence_evidence must be an object")
    validate_native_first_candidate_matrix(matrix)

    evidence_sha256 = _required_sha256(receipt.get("evidence_sha256"), "evidence_sha256")
    calculated_evidence = _sha256(binding)
    if calculated_evidence != evidence_sha256:
        raise ValueError("evidence_sha256 does not match evidence_binding")

    matrix_sha256 = _required_sha256(receipt.get("matrix_sha256"), "matrix_sha256")
    candidate_sha256 = _required_sha256(
        receipt.get("candidate_sha256"), "candidate_sha256"
    )
    independence_evidence_sha256 = _required_sha256(
        receipt.get("independence_evidence_sha256"),
        "independence_evidence_sha256",
    )
    if matrix_sha256 != _sha256(matrix):
        raise ValueError("matrix_sha256 does not match embedded matrix")
    if candidate_sha256 != _sha256(candidate):
        raise ValueError("candidate_sha256 does not match embedded candidate")
    if independence_evidence_sha256 != _sha256(independence_evidence):
        raise ValueError(
            "independence_evidence_sha256 does not match embedded independence evidence"
        )

    qualification_id = _required_string(
        receipt.get("qualification_id"), "qualification_id"
    )
    expected_id = f"{QUALIFICATION_ID_PREFIX}{evidence_sha256[:24]}"
    if qualification_id != expected_id:
        raise ValueError("qualification_id is not derived from evidence_sha256")

    (
        matrix_id,
        provider_contract,
        independence,
        evaluation,
        candidate_id,
        family,
    ) = _recompute(
        candidate=candidate,
        independence_evidence=independence_evidence,
        matrix=matrix,
    )

    expected_qualified = evaluation.eligible and independence.passed
    expected_values = {
        "matrix_id": matrix_id,
        "candidate_id": candidate_id,
        "model_id": independence.model_id,
        "family": family,
        "artifact_sha256": independence.artifact_sha256,
        "provider_contract": provider_contract,
        "independence_gate_id": independence.gate_id,
        "independence_passed": independence.passed,
        "qualified": expected_qualified,
        "score": evaluation.score,
        "hard_gate_failures": evaluation.hard_gate_failures,
        "missing_metrics": evaluation.missing_metrics,
    }
    for label, expected in expected_values.items():
        if receipt.get(label) != expected:
            raise ValueError(f"{label} does not match recomputed qualification evidence")

    if expected_qualified and evaluation.score is None:
        raise ValueError("qualified receipt requires a numeric score")


def qualify_candidate(
    candidate: dict[str, Any],
    independence_evidence: dict[str, Any],
    matrix: dict[str, Any],
) -> NativeQualification:
    frozen_matrix = _frozen_json(matrix)
    frozen_candidate = _frozen_json(candidate)
    frozen_independence = _frozen_json(independence_evidence)
    validate_native_first_candidate_matrix(frozen_matrix)

    (
        matrix_id,
        provider_contract,
        independence,
        evaluation,
        candidate_id,
        family,
    ) = _recompute(
        candidate=frozen_candidate,
        independence_evidence=frozen_independence,
        matrix=frozen_matrix,
    )

    evidence_binding = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "matrix": frozen_matrix,
        "candidate": frozen_candidate,
        "independence_evidence": frozen_independence,
    }
    evidence_sha256 = _sha256(evidence_binding)
    qualification_id = f"{QUALIFICATION_ID_PREFIX}{evidence_sha256[:24]}"

    result = NativeQualification(
        schema_version=QUALIFICATION_SCHEMA_VERSION,
        qualification_id=qualification_id,
        matrix_id=matrix_id,
        matrix_sha256=_sha256(frozen_matrix),
        candidate_id=candidate_id,
        candidate_sha256=_sha256(frozen_candidate),
        model_id=independence.model_id,
        family=family,
        artifact_sha256=independence.artifact_sha256,
        provider_contract=provider_contract,
        qualified=evaluation.eligible and independence.passed,
        score=evaluation.score,
        hard_gate_failures=evaluation.hard_gate_failures,
        missing_metrics=evaluation.missing_metrics,
        independence_gate_id=independence.gate_id,
        independence_passed=independence.passed,
        independence_evidence_sha256=_sha256(frozen_independence),
        evidence_binding=evidence_binding,
        evidence_sha256=evidence_sha256,
    )
    verify_qualification_receipt(result.to_dict())
    return result
