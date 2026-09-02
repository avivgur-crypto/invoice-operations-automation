"""Local JSON adapter used for demos, development, and repeatable tests."""

import json
from pathlib import Path

from invoice_ops.models import Invoice


def load_invoices(path: Path) -> list[Invoice]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Invoice source must contain a JSON array")
    invoices = [Invoice.model_validate(item) for item in payload]
    ids = [item.external_id for item in invoices]
    if len(ids) != len(set(ids)):
        raise ValueError("Invoice source contains duplicate external_id values")
    return invoices
