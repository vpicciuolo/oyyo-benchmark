from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

from .candidates import evaluate_candidate
from .independence import evaluate_independence


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
QUALIFICATION_SCHEMA_VERSION = "0.1"
QUALIFICATION_ID_PREFIX = "oyyo-qualification-"


@dataclass
class NativeQualification:
    schema_version: str
    qualification_id: str
    matrix_id: str
    candidate_id: str
    model_id: str
    family: str
    artifact_sha256: str
    qualified: bool
    score: float | None
    hard_gate_failures: list[str]
    missing_metrics: list[str]
    independence_gate_id: str
    independence_passed: bool
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


def _frozen_json(value: Any) -> Any:
    """Detach qualification evidence from caller-owned mutable objects."""
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def verify_qualification_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("schema_version") != QUALIFICATION_SCHEMA_VERSION:
        raise ValueError("qualification schema_version must be 0.1")

    evidence_sha256 = _required_string(
        receipt.get("evidence_sha256"), "evidence_sha256"
    ).lower()
    if not _SHA256.fullmatch(evidence_sha256):
        raise ValueError("evidence_sha256 must be a lowercase SHA-256 digest")

    binding = receipt.get("evidence_binding")
    if not isinstance(binding, dict):
        raise ValueError("evidence_binding must be an object")
    calculated = hashlib.sha256(_canonical_bytes(binding)).hexdigest()
    if calculated != evidence_sha256:
        raise ValueError("evidence_sha256 does not match evidence_binding")

    qualification_id = _required_string(
        receipt.get("qualification_id"), "qualification_id"
    )
    expected_id = f"{QUALIFICATION_ID_PREFIX}{evidence_sha256[:24]}"
    if qualification_id != expected_id:
        raise ValueError("qualification_id is not derived from evidence_sha256")

    matrix_id = _required_string(receipt.get("matrix_id"), "matrix_id")
    candidate_id = _required_string(receipt.get("candidate_id"), "candidate_id")
    model_id = _required_string(receipt.get("model_id"), "model_id")
    family = _required_string(receipt.get("family"), "family")
    artifact_sha256 = _required_string(
        receipt.get("artifact_sha256"), "artifact_sha256"
    ).lower()
    if not _SHA256.fullmatch(artifact_sha256):
        raise ValueError("artifact_sha256 must be a lowercase SHA-256 digest")
    independence_gate_id = _required_string(
        receipt.get("independence_gate_id"), "independence_gate_id"
    )

    if binding.get("schema_version") != QUALIFICATION_SCHEMA_VERSION:
        raise ValueError("evidence_binding schema_version must be 0.1")
    if binding.get("matrix_id") != matrix_id:
        raise ValueError("matrix_id does not match evidence_binding")

    bound_candidate = binding.get("candidate")
    if not isinstance(bound_candidate, dict):
        raise ValueError("evidence_binding.candidate must be an object")
    if bound_candidate.get("candidate_id") != candidate_id:
        raise ValueError("candidate_id does not match evidence_binding")
    if bound_candidate.get("family") != family:
        raise ValueError("family does not match evidence_binding candidate")

    independence = binding.get("independence")
    if not isinstance(independence, dict):
        raise ValueError("evidence_binding.independence must be an object")
    for label, expected in [
        ("candidate_id", candidate_id),
        ("model_id", model_id),
        ("family", family),
        ("artifact_sha256", artifact_sha256),
        ("gate_id", independence_gate_id),
        ("passed", receipt.get("independence_passed")),
    ]:
        if independence.get(label) != expected:
            raise ValueError(f"{label} does not match embedded independence evidence")

    qualified = receipt.get("qualified")
    if not isinstance(qualified, bool):
        raise ValueError("qualified must be boolean")
    independence_passed = receipt.get("independence_passed")
    if not isinstance(independence_passed, bool):
        raise ValueError("independence_passed must be boolean")
    hard_gate_failures = receipt.get("hard_gate_failures")
    missing_metrics = receipt.get("missing_metrics")
    if not isinstance(hard_gate_failures, list) or not all(
        isinstance(value, str) for value in hard_gate_failures
    ):
        raise ValueError("hard_gate_failures must be a list of strings")
    if not isinstance(missing_metrics, list) or not all(
        isinstance(value, str) for value in missing_metrics
    ):
        raise ValueError("missing_metrics must be a list of strings")

    if qualified:
        if not independence_passed:
            raise ValueError("qualified receipt requires independence_passed=true")
        if hard_gate_failures or missing_metrics:
            raise ValueError("qualified receipt cannot contain gate or metric failures")
        score = receipt.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("qualified receipt requires a numeric score")


def qualify_candidate(
    candidate: dict[str, Any],
    independence_evidence: dict[str, Any],
    matrix: dict[str, Any],
) -> NativeQualification:
    independence = evaluate_independence(independence_evidence, matrix)
    candidate_id = str(candidate.get("candidate_id", "")).strip()
    family = str(candidate.get("family", "")).strip()
    if candidate_id != independence.candidate_id:
        raise ValueError(
            "candidate_id does not match the validated independence evidence"
        )
    if family != independence.family:
        raise ValueError("candidate family does not match the independence evidence")

    evaluation = evaluate_candidate(
        candidate,
        matrix,
        {"independence_test_passed": independence.passed},
    )
    matrix_id = str(matrix.get("matrix_id", "")).strip()
    if not matrix_id:
        raise ValueError("matrix_id is required")

    evidence_binding = _frozen_json(
        {
            "schema_version": QUALIFICATION_SCHEMA_VERSION,
            "matrix_id": matrix_id,
            "candidate": candidate,
            "independence": independence.to_dict(),
        }
    )
    evidence_sha256 = hashlib.sha256(_canonical_bytes(evidence_binding)).hexdigest()
    qualification_id = f"{QUALIFICATION_ID_PREFIX}{evidence_sha256[:24]}"

    result = NativeQualification(
        schema_version=QUALIFICATION_SCHEMA_VERSION,
        qualification_id=qualification_id,
        matrix_id=matrix_id,
        candidate_id=candidate_id,
        model_id=independence.model_id,
        family=family,
        artifact_sha256=independence.artifact_sha256,
        qualified=evaluation.eligible and independence.passed,
        score=evaluation.score,
        hard_gate_failures=evaluation.hard_gate_failures,
        missing_metrics=evaluation.missing_metrics,
        independence_gate_id=independence.gate_id,
        independence_passed=independence.passed,
        evidence_binding=evidence_binding,
        evidence_sha256=evidence_sha256,
    )
    verify_qualification_receipt(result.to_dict())
    return result
