from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidates import load_json, rank_candidates
from .independence import evaluate_independence
from .runner import run_foundation_smoke, save_result


def main(argv=None):
    parser = argparse.ArgumentParser(prog="oyyo-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--output")

    independence_evaluate = sub.add_parser(
        "independence-evaluate",
        help="Validate native isolation plus required OYYO workflow evidence.",
    )
    independence_evaluate.add_argument("--matrix", required=True)
    independence_evaluate.add_argument("--evidence", required=True)
    independence_evaluate.add_argument("--output")

    candidate_evaluate = sub.add_parser(
        "candidate-evaluate",
        help="Evaluate and rank OYYO Mini/Nano candidates against a versioned matrix.",
    )
    candidate_evaluate.add_argument("--matrix", required=True)
    candidate_evaluate.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Candidate evidence JSON. Repeat to compare multiple candidates.",
    )
    candidate_evaluate.add_argument(
        "--independence-evidence",
        action="append",
        default=[],
        help=(
            "Validated native independence/workflow evidence. Repeat for multiple candidates. "
            "A candidate self-assertion cannot satisfy the independence gate."
        ),
    )
    candidate_evaluate.add_argument("--output")

    args = parser.parse_args(argv)

    if args.command == "smoke":
        result = run_foundation_smoke()
        if args.output:
            save_result(args.output, result)
        print(json.dumps(result.to_dict(), indent=2))
        raise SystemExit(0 if result.passed else 1)

    if args.command == "independence-evaluate":
        matrix = load_json(args.matrix)
        evidence = load_json(args.evidence)
        result = evaluate_independence(evidence, matrix)
        rendered = json.dumps(result.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        raise SystemExit(0 if result.passed else 1)

    if args.command == "candidate-evaluate":
        matrix = load_json(args.matrix)
        candidates = [load_json(path) for path in args.candidate]
        independence_results = [
            evaluate_independence(load_json(path), matrix)
            for path in args.independence_evidence
        ]
        verified: dict[str, dict[str, bool]] = {}
        for result in independence_results:
            if result.candidate_id in verified:
                raise ValueError(
                    f"duplicate independence evidence for candidate {result.candidate_id}"
                )
            verified[result.candidate_id] = {
                "independence_test_passed": result.passed
            }

        evaluations = rank_candidates(candidates, matrix, verified)
        payload = {
            "matrix_id": matrix.get("matrix_id"),
            "independence": [result.to_dict() for result in independence_results],
            "results": [result.to_dict() for result in evaluations],
        }
        rendered = json.dumps(payload, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        raise SystemExit(0 if any(result.eligible for result in evaluations) else 1)


if __name__ == "__main__":
    main()
