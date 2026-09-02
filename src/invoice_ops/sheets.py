"""Google Sheets destination adapter."""

from collections.abc import Iterable
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from invoice_ops.config import Settings
from invoice_ops.models import Invoice
from invoice_ops.reconciliation import ActionType, SyncAction

HEADERS = [
    "Month",
    "Document Date",
    "Vendor",
    "Amount",
    "Tax",
    "Document Type",
    "Currency",
    "Category",
    "Business Unit",
    "Document Number",
    "External ID",
    "Source Updated At",
    "Status",
    "Review Reason",
]


class GoogleSheetsGateway:
    """Reads canonical invoices and applies an approved sync plan."""

    def __init__(self, settings: Settings) -> None:
        settings.require_google_configuration()
        credentials = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            str(settings.google_credentials_file),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(credentials)
        workbook = client.open_by_key(settings.spreadsheet_id)
        self.sheet = workbook.worksheet(settings.worksheet_name)
        self.archive = workbook.worksheet(settings.archive_worksheet_name)
        self._ensure_headers()

    def _ensure_headers(self) -> None:
        if self.sheet.row_values(1) != HEADERS:
            self.sheet.update([HEADERS], range_name="A1:N1")
        if self.archive.row_values(1) != HEADERS:
            self.archive.update([HEADERS], range_name="A1:N1")

    def read(self) -> list[Invoice]:
        values = self.sheet.get_all_records()
        invoices: list[Invoice] = []
        for row in values:
            external_id = str(row.get("External ID", "")).strip()
            if not external_id:
                continue
            invoices.append(
                Invoice.model_validate(
                    {
                        "external_id": external_id,
                        "document_date": row["Document Date"],
                        "vendor": row["Vendor"],
                        "amount": row["Amount"],
                        "tax": row.get("Tax", 0),
                        "currency": row["Currency"],
                        "category": row.get("Category", ""),
                        "business_unit": row.get("Business Unit", ""),
                        "document_number": str(row.get("Document Number", "")),
                        "document_type": row.get("Document Type", "invoice"),
                        "source_updated_at": row.get("Source Updated At") or None,
                    }
                )
            )
        return invoices

    def apply(self, actions: Iterable[SyncAction]) -> dict[str, int]:
        rows: list[list[Any]] = self.sheet.get_all_values()
        row_by_id = {
            row[10]: index
            for index, row in enumerate(rows[1:], start=2)
            if len(row) > 10 and row[10]
        }
        counts = {action.value: 0 for action in ActionType}

        for action in actions:
            counts[action.action.value] += 1
            row_number = row_by_id.get(action.external_id)

            if action.action is ActionType.ADD and action.incoming:
                self.sheet.append_row(action.incoming.to_sheet_row())
            elif action.action is ActionType.UPDATE and action.incoming and row_number:
                self.sheet.update(
                    [action.incoming.to_sheet_row()],
                    range_name=f"A{row_number}:N{row_number}",
                )
            elif action.action is ActionType.REVIEW and row_number:
                self.sheet.update(
                    [["NEEDS_REVIEW", action.reason]],
                    range_name=f"M{row_number}:N{row_number}",
                )
            elif action.action is ActionType.ARCHIVE and action.existing and row_number:
                self.archive.append_row(
                    action.existing.to_sheet_row(
                        status="ARCHIVED",
                        review_reason=action.reason,
                    )
                )
                self.sheet.delete_rows(row_number)
                row_by_id = {
                    key: value - 1 if value > row_number else value
                    for key, value in row_by_id.items()
                    if key != action.external_id
                }

        return counts
