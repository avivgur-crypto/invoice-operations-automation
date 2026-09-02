from decimal import Decimal

from invoice_ops.models import Invoice
from invoice_ops.reconciliation import ActionType, reconcile


def invoice(external_id: str, amount: str = "100", category: str = "Software") -> Invoice:
    return Invoice(
        external_id=external_id,
        document_date="2026-08-01",
        vendor="Example Vendor",
        amount=Decimal(amount),
        currency="usd",
        category=category,
    )


def test_builds_add_update_and_archive_plan() -> None:
    existing = [invoice("keep", "100"), invoice("archive", "25")]
    incoming = [invoice("keep", "110"), invoice("new", "80")]

    actions = reconcile(existing, incoming)

    assert [(action.external_id, action.action) for action in actions] == [
        ("new", ActionType.ADD),
        ("keep", ActionType.UPDATE),
        ("archive", ActionType.ARCHIVE),
    ]


def test_large_amount_change_is_sent_to_review() -> None:
    actions = reconcile([invoice("inv-1", "100")], [invoice("inv-1", "175")])

    assert actions[0].action is ActionType.REVIEW
    assert "75%" in actions[0].reason


def test_category_removal_is_sent_to_review() -> None:
    actions = reconcile(
        [invoice("inv-1", category="Software")],
        [invoice("inv-1", category="")],
    )

    assert actions[0].action is ActionType.REVIEW
    assert "Category became empty" in actions[0].reason


def test_currency_is_normalized() -> None:
    assert invoice("inv-1").currency == "USD"
