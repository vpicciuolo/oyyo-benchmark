from __future__ import annotations
import argparse, json
from .runner import run_foundation_smoke, save_result

def main(argv=None):
    parser = argparse.ArgumentParser(prog="oyyo-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--output")
    args = parser.parse_args(argv)

    if args.command == "smoke":
        result = run_foundation_smoke()
        if args.output:
            save_result(args.output, result)
        print(json.dumps(result.to_dict(), indent=2))
        raise SystemExit(0 if result.passed else 1)

if __name__ == "__main__":
    main()
