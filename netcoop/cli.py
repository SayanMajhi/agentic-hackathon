"""netcoop CLI.

    netcoop run scenarios/dev/sample_minimal.json [--local] [--control]
    netcoop export-schemas
    netcoop eval --n 50 --noise --seed 7          (TODO: Backend 1)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from netcoop.orchestrator.run import REPO_ROOT, _terminal, load_signatures, run_incident, write_outputs
from netcoop.protocol.models import Status


def cmd_run(args: argparse.Namespace) -> int:
    signatures = load_signatures()
    topology = json.loads(Path(args.topology).read_text(encoding="utf-8"))
    try:
        raw = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = _terminal(Path(args.scenario).stem, Status.invalid_input, signatures,
                           validation_errors=[f"cannot parse scenario: {exc}"])
        print(json.dumps(report.model_dump(mode="json"), indent=2))
        return 0
    result = run_incident(raw, topology, signatures,
                          connectivity="local" if args.local else "remote",
                          endpoint=args.endpoint, drop_peer_findings=args.control)
    rp, tp = write_outputs(result, Path(args.out), Path(args.traces))
    print(json.dumps(result.report.model_dump(mode="json"), indent=2))
    print(f"\nreport: {rp}\ntrace:  {tp}", file=sys.stderr)
    return 0


def cmd_export(_: argparse.Namespace) -> int:
    from netcoop.protocol.export import main as export_main
    export_main([])
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    print("TODO(Backend 1): held-out evaluation — confusion matrix, false-diagnosis rate, "
          "abstention by class, evidence-link integrity", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="netcoop")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="diagnose one scenario")
    r.add_argument("scenario")
    r.add_argument("--topology", default=str(REPO_ROOT / "scenarios" / "topology.json"))
    r.add_argument("--out", default=str(REPO_ROOT / "reports"))
    r.add_argument("--traces", default=str(REPO_ROOT / "traces"))
    r.add_argument("--endpoint", default=None, help="Connectivity URL (default from agent card)")
    r.add_argument("--local", action="store_true", help="run Connectivity in-process (tests only)")
    r.add_argument("--control", action="store_true", help="control run: no peer findings to Connectivity")
    r.set_defaults(func=cmd_run)

    sub.add_parser("export-schemas", help="regenerate schemas/ and PROTOCOL.md").set_defaults(func=cmd_export)

    e = sub.add_parser("eval", help="held-out evaluation")
    e.add_argument("--n", type=int, default=50)
    e.add_argument("--noise", action="store_true")
    e.add_argument("--seed", type=int, default=7)
    e.set_defaults(func=cmd_eval)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
