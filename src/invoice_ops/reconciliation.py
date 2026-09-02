"""Pure reconciliation logic: deterministic, testable, and auditable."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from invoice_ops.models import Invoice


class ActionType(StrEnum):
    ADD = "add"
    UPDATE = "update"
    ARCHIVE = "archive"
    REVIEW = "review"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class SyncAction:
    action: ActionType
    external_id: str
    incoming: Invoice | None = None
    existing: Invoice | None = None
    reason: str = ""


def material_fields(invoice: Invoice) -> tuple[object, ...]:
    return (
        invoice.document_date,
        invoice.vendor.strip(),
        invoice.signed_amount(),
        invoice.tax,
        invoice.currency,
        invoice.category.strip(),
        invoice.business_unit.strip(),
        invoice.document_number.strip(),
        invoice.document_type,
    )


def review_reason(existing: Invoice, incoming: Invoice, threshold: float) -> str:
    """Return a reason when an update needs human approval."""

    if existing.category and not incoming.category:
        return f"Category became empty (was: {existing.category})"
    if existing.business_unit and not incoming.business_unit:
        return f"Business unit became empty (was: {existing.business_unit})"
    if existing.vendor and not incoming.vendor:
        return f"Vendor became empty (was: {existing.vendor})"

    old_amount = abs(existing.signed_amount())
    new_amount = abs(incoming.signed_amount())
    if old_amount > 0 and new_amount == 0:
        return f"Amount became zero (was: {old_amount})"
    if old_amount > 0:
        change = abs(new_amount - old_amount) / old_amount
        if change > Decimal(str(threshold)):
            return f"Amount changed by {change:.0%}: {old_amount} -> {new_amount}"

    if existing.signed_amount() * incoming.signed_amount() < 0:
        return (
            "Amount sign changed: "
            f"{existing.signed_amount()} -> {incoming.signed_amount()}"
        )
    return ""


def reconcile(
    existing: Iterable[Invoice],
    incoming: Iterable[Invoice],
    *,
    review_threshold: float = 0.50,
) -> list[SyncAction]:
    """Build an ordered plan without mutating the destination."""

    existing_map = {item.external_id: item for item in existing}
    incoming_map = {item.external_id: item for item in incoming}
    actions: list[SyncAction] = []

    for external_id in sorted(incoming_map.keys() - existing_map.keys()):
        actions.append(
            SyncAction(ActionType.ADD, external_id, incoming=incoming_map[external_id])
        )

    for external_id in sorted(incoming_map.keys() & existing_map.keys()):
        old = existing_map[external_id]
        new = incoming_map[external_id]
        if material_fields(old) == material_fields(new):
            actions.append(
                SyncAction(ActionType.UNCHANGED, external_id, incoming=new, existing=old)
            )
            continue
        reason = review_reason(old, new, review_threshold)
        actions.append(
            SyncAction(
                ActionType.REVIEW if reason else ActionType.UPDATE,
                external_id,
                incoming=new,
                existing=old,
                reason=reason,
            )
        )

    for external_id in sorted(existing_map.keys() - incoming_map.keys()):
        actions.append(
            SyncAction(
                ActionType.ARCHIVE,
                external_id,
                existing=existing_map[external_id],
                reason="No longer present in source",
            )
        )

    return actions
