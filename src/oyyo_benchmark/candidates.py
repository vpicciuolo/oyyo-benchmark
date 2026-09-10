from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


_VERIFIED_HARD_GATES = {"independence_test_passed"}


@dataclass
class CandidateEvaluation:
    candidate_id: str
    family: str
    eligible: bool
    score: float | None
    hard_gate_failures: list[str]
    missing_metrics: list[str]
    metric_scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalized_score(value: float, spec: dict[str, Any]) -> float:
    lower = float(spec["min"])
    upper = float(spec["max"])
    if upper <= lower:
        raise ValueError(
            f"invalid metric range for {spec.get('id', 'metric')}: max must be > min"
        )
    clamped = min(max(float(value), lower), upper)
    if spec["direction"] == "higher_is_better":
        normalized = (clamped - lower) / (upper - lower)
    elif spec["direction"] == "lower_is_better":
        normalized = (upper - clamped) / (upper - lower)
    else:
        raise ValueError(f"unsupported metric direction: {spec['direction']}")
    return round(normalized * 100.0, 6)


def evaluate_candidate(
    candidate: dict[str, Any],
    matrix: dict[str, Any],
    verified_hard_gates: dict[str, bool] | None = None,
) -> CandidateEvaluation:
    candidate_id = str(candidate.get("candidate_id", "")).strip()
    family = str(candidate.get("family", "")).strip()
    if not candidate_id:
        raise ValueError("candidate_id is required")

    profiles = matrix.get("family_profiles", {})
    if family not in profiles:
        raise ValueError(f"unsupported candidate family: {family}")

    hard_evidence = candidate.get("hard_gates")
    if not isinstance(hard_evidence, dict):
        hard_evidence = {}
    verified_hard_gates = verified_hard_gates or {}

    hard_gate_failures: list[str] = []
    for gate in matrix.get("hard_gates", []):
        gate_id = gate["id"]
        if gate_id in _VERIFIED_HARD_GATES:
            passed = verified_hard_gates.get(gate_id) is True
        else:
            passed = hard_evidence.get(gate_id) is True
        if not passed:
            hard_gate_failures.append(gate_id)

    metrics = candidate.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}

    profile = profiles[family]
    metric_specs = profile.get("metrics", [])
    missing_metrics: list[str] = []
    metric_scores: dict[str, float] = {}
    weighted = 0.0
    total_weight = 0.0

    for spec in metric_specs:
        metric_id = spec["id"]
        if metric_id not in metrics:
            missing_metrics.append(metric_id)
            continue
        normalized = _normalized_score(float(metrics[metric_id]), spec)
        metric_scores[metric_id] = normalized
        weight = float(spec["weight"])
        weighted += normalized * weight
        total_weight += weight

    eligible = not hard_gate_failures and not missing_metrics
    score = None
    if eligible:
        if total_weight <= 0:
            raise ValueError(f"family profile {family} has no positive metric weight")
        score = round(weighted / total_weight, 3)

    return CandidateEvaluation(
        candidate_id=candidate_id,
        family=family,
        eligible=eligible,
        score=score,
        hard_gate_failures=hard_gate_failures,
        missing_metrics=missing_metrics,
        metric_scores=metric_scores,
    )


def rank_candidates(
    candidates: list[dict[str, Any]],
    matrix: dict[str, Any],
    verified_hard_gates_by_candidate: dict[str, dict[str, bool]] | None = None,
) -> list[CandidateEvaluation]:
    verified_hard_gates_by_candidate = verified_hard_gates_by_candidate or {}
    evaluations = [
        evaluate_candidate(
            candidate,
            matrix,
            verified_hard_gates_by_candidate.get(str(candidate.get("candidate_id", "")), {}),
        )
        for candidate in candidates
    ]
    return sorted(
        evaluations,
        key=lambda result: (
            not result.eligible,
            -(result.score if result.score is not None else -1.0),
            result.candidate_id,
        ),
    )
