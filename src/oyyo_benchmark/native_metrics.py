from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any

from .native_evidence import validate_workflow_output


_GIB = 1024**3


@dataclass
class CaseResult:
    case_id: str
    metric_id: str
    passed: bool
    reason: str | None


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def evaluate_native_metrics(
    suite: dict[str, Any], observations: dict[str, dict[str, Any]]
) -> tuple[dict[str, float], list[CaseResult]]:
    if suite.get("schema_version") != "0.1":
        raise ValueError("scoring suite schema_version must be 0.1")
    metric_specs = _required_dict(suite.get("metrics"), "suite.metrics")
    if not metric_specs:
        raise ValueError("suite.metrics must not be empty")

    expected_case_ids: set[str] = set()
    case_results: list[CaseResult] = []
    metric_scores: dict[str, float] = {}

    for metric_id, metric_value in metric_specs.items():
        metric = _required_dict(metric_value, f"suite.metrics.{metric_id}")
        cases = metric.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"suite metric {metric_id} cases must be non-empty")
        passed_count = 0
        for case_value in cases:
            case = _required_dict(case_value, f"suite.metrics.{metric_id}.case")
            case_id = _required_string(case.get("id"), "case.id")
            if case_id in expected_case_ids:
                raise ValueError(f"duplicate scoring case id: {case_id}")
            expected_case_ids.add(case_id)
            observation = observations.get(case_id)
            if not isinstance(observation, dict):
                raise ValueError(f"missing observation for scoring case {case_id}")
            output_text = _required_string(observation.get("output_text"), f"{case_id}.output_text")
            validation = validate_workflow_output(case_id, output_text, case)
            if validation.passed:
                passed_count += 1
            case_results.append(
                CaseResult(
                    case_id=case_id,
                    metric_id=metric_id,
                    passed=validation.passed,
                    reason=validation.reason,
                )
            )
        metric_scores[metric_id] = round(100.0 * passed_count / len(cases), 6)

    extra = sorted(set(observations) - expected_case_ids)
    if extra:
        raise ValueError(f"unexpected scoring observations: {extra}")

    first_token_values: list[float] = []
    peak_rss_values: list[int] = []
    for case_id, observation in observations.items():
        first_token = observation.get("first_output_byte_ms")
        if not isinstance(first_token, (int, float)) or isinstance(first_token, bool) or first_token < 0:
            raise ValueError(f"{case_id}.first_output_byte_ms must be non-negative")
        first_token_values.append(float(first_token))
        peak_rss = observation.get("peak_rss_bytes")
        if not isinstance(peak_rss, int) or isinstance(peak_rss, bool) or peak_rss <= 0:
            raise ValueError(f"{case_id}.peak_rss_bytes must be a positive integer")
        peak_rss_values.append(peak_rss)

    metric_scores["peak_ram_gib"] = round(max(peak_rss_values) / _GIB, 6)
    metric_scores["p50_first_token_ms"] = round(float(median(first_token_values)), 6)
    return metric_scores, case_results
