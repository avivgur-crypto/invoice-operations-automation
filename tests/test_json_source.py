import json
from pathlib import Path

import pytest

from invoice_ops.json_source import load_invoices


def test_rejects_duplicate_external_ids(tmp_path: Path) -> None:
    path = tmp_path / "invoices.json"
    row = {
        "external_id": "same",
        "document_date": "2026-08-01",
        "vendor": "Example",
        "amount": "20",
        "currency": "USD",
    }
    path.write_text(json.dumps([row, row]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_invoices(path)
