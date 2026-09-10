from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidates import load_json, rank_candidates
from .independence import evaluate_independence
from .native_evidence import assemble_independence_evidence
from .qualification import qualify_candidate, verify_qualification_receipt
from .runner import run_foundation_smoke, save_result


def _workflow_receipts(values: list[str]) -> dict[str, dict]:
    receipts: dict[str, dict] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--receipt must use workflow=path syntax")
        workflow_id, path = value.split("=", 1)
        workflow_id = workflow_id.strip()
        path = path.strip()
        if not workflow_id or not path:
            raise ValueError("--receipt must use non-empty workflow=path syntax")
        if workflow_id in receipts:
            raise ValueError(f"duplicate provider receipt for workflow {workflow_id}")
        receipts[workflow_id] = load_json(path)
    return receipts


def main(argv=None):
    parser = argparse.ArgumentParser(prog="oyyo-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--output")

    native_evidence = sub.add_parser(
        "native-evidence-assemble",
        help="Validate OYYO native-provider workflow receipts and assemble independence evidence.",
    )
    native_evidence.add_argument("--suite", required=True)
    native_evidence.add_argument("--candidate-id", required=True)
    native_evidence.add_argument("--family", required=True)
    native_evidence.add_argument(
        "--receipt",
        action="append",
        required=True,
        help="Provider evaluation receipt as workflow=path. Repeat once per suite workflow.",
    )
    native_evidence.add_argument("--output")

    independence_evaluate = sub.add_parser(
        "independence-evaluate",
        help="Validate native isolation plus required OYYO workflow evidence.",
    )
    independence_evaluate.add_argument("--matrix", required=True)
    independence_evaluate.add_argument("--evidence", required=True)
    independence_evaluate.add_argument("--output")

    qualification_evaluate = sub.add_parser(
        "qualification-evaluate",
        help="Create a deterministic qualification record bound to candidate and native evidence.",
    )
    qualification_evaluate.add_argument("--matrix", required=True)
    qualification_evaluate.add_argument("--candidate", required=True)
    qualification_evaluate.add_argument("--independence-evidence", required=True)
    qualification_evaluate.add_argument("--output")

    qualification_verify = sub.add_parser(
        "qualification-verify",
        help="Verify a qualification receipt and its embedded canonical evidence binding.",
    )
    qualification_verify.add_argument("--receipt", required=True)

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

    if args.command == "native-evidence-assemble":
        suite = load_json(args.suite)
        receipts = _workflow_receipts(args.receipt)
        evidence, validations = assemble_independence_evidence(
            receipts,
            suite,
            candidate_id=args.candidate_id,
            family=args.family,
        )
        payload = {
            "suite_id": suite.get("suite_id"),
            "validations": [
                {
                    "workflow_id": item.workflow_id,
                    "passed": item.passed,
                    "reason": item.reason,
                }
                for item in validations
            ],
            "evidence": evidence,
        }
        rendered = json.dumps(payload, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        raise SystemExit(0 if all(item.passed for item in validations) else 1)

    if args.command == "independence-evaluate":
        matrix = load_json(args.matrix)
        evidence = load_json(args.evidence)
        result = evaluate_independence(evidence, matrix)
        rendered = json.dumps(result.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        raise SystemExit(0 if result.passed else 1)

    if args.command == "qualification-evaluate":
        matrix = load_json(args.matrix)
        candidate = load_json(args.candidate)
        independence_evidence = load_json(args.independence_evidence)
        result = qualify_candidate(candidate, independence_evidence, matrix)
        rendered = json.dumps(result.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        raise SystemExit(0 if result.qualified else 1)

    if args.command == "qualification-verify":
        receipt = load_json(args.receipt)
        verify_qualification_receipt(receipt)
        print(
            json.dumps(
                {
                    "valid": True,
                    "qualification_id": receipt["qualification_id"],
                    "candidate_id": receipt["candidate_id"],
                    "model_id": receipt["model_id"],
                    "artifact_sha256": receipt["artifact_sha256"],
                    "qualified": receipt["qualified"],
                },
                indent=2,
            )
        )
        raise SystemExit(0)

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
