from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .candidates import evaluate_candidate
from .independence import evaluate_independence


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

    evidence_binding = {
        "schema_version": "0.1",
        "matrix_id": matrix_id,
        "candidate": candidate,
        "independence": independence.to_dict(),
    }
    evidence_sha256 = hashlib.sha256(_canonical_bytes(evidence_binding)).hexdigest()
    qualification_id = f"oyyo-qualification-{evidence_sha256[:24]}"

    return NativeQualification(
        schema_version="0.1",
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
        evidence_sha256=evidence_sha256,
    )
