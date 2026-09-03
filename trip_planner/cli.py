"""Command-line entry point for the trip planning research agent.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m trip_planner.cli --destination "Lisbon, Portugal" \\
        --start-date 2026-10-10 --end-date 2026-10-17 \\
        --budget 2200 --currency USD
"""

from __future__ import annotations

import argparse
import json
import sys

from .agent import DEFAULT_MODEL, TripPlanRequest, plan_trip


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Research flights, accommodation, and activities for a trip and "
        "return a structured JSON trip plan.",
    )
    parser.add_argument("--destination", required=True, help="e.g. 'Lisbon, Portugal'")
    parser.add_argument("--start-date", required=True, help="Travel start date, e.g. 2026-10-10")
    parser.add_argument("--end-date", required=True, help="Travel end date, e.g. 2026-10-17")
    parser.add_argument("--budget", required=True, type=float, help="Total trip budget, e.g. 2200")
    parser.add_argument("--currency", default="USD", help="ISO currency code for the budget (default: USD)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Reasoning/output effort level (default: high)",
    )
    parser.add_argument("--max-tokens", default=16000, type=int, help="Max output tokens (default: 16000)")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    request = TripPlanRequest(
        destination=args.destination,
        start_date=args.start_date,
        end_date=args.end_date,
        budget_amount=args.budget,
        budget_currency=args.currency,
    )

    try:
        plan = plan_trip(
            request,
            model=args.model,
            max_tokens=args.max_tokens,
            effort=args.effort,
        )
    except Exception as exc:  # surface a clean message instead of a raw traceback
        print(f"Trip planning failed: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(plan, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
