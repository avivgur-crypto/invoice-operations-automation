"""Command-line entrypoint with dry-run as the safe default."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

from invoice_ops.config import Settings
from invoice_ops.json_source import load_invoices
from invoice_ops.models import Invoice
from invoice_ops.reconciliation import ActionType, SyncAction, reconcile
from invoice_ops.sheets import GoogleSheetsGateway


def serialize_action(action: SyncAction) -> dict[str, object]:
    return {
        "action": action.action.value,
        "external_id": action.external_id,
        "reason": action.reason,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile invoice records with an auditable, review-first workflow."
    )
    parser.add_argument("--source", type=Path, help="JSON file containing source invoices")
    parser.add_argument(
        "--existing",
        type=Path,
        help="Optional JSON snapshot for a fully local reconciliation demo",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the plan to Google Sheets; otherwise run safely in dry-run mode",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings()
    source_path = args.source or settings.source_file
    incoming = load_invoices(source_path)

    gateway: GoogleSheetsGateway | None = None
    existing: list[Invoice]
    if args.existing:
        existing = load_invoices(args.existing)
    elif args.apply:
        gateway = GoogleSheetsGateway(settings)
        existing = gateway.read()
    else:
        existing = []

    plan = reconcile(
        existing,
        incoming,
        review_threshold=settings.review_threshold,
    )
    print(json.dumps([serialize_action(action) for action in plan], indent=2))
    summary = Counter(action.action.value for action in plan)
    print("\nSummary:", dict(summary))

    if not args.apply:
        print("Dry run only. Re-run with --apply to write to Google Sheets.")
        return 0

    assert gateway is not None
    blocked = summary[ActionType.REVIEW.value]
    if blocked:
        print(f"Applied safe actions; {blocked} suspicious change(s) remain for review.")
    counts = gateway.apply(plan)
    print("Applied:", counts)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
