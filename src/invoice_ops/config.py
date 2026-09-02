"""Validated runtime configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INVOICE_OPS_",
        extra="ignore",
    )

    source_file: Path = Path("examples/sample_invoices.json")
    spreadsheet_id: str = ""
    worksheet_name: str = "Invoices"
    archive_worksheet_name: str = "Archive"
    google_credentials_file: Path = Path("credentials.json")
    review_threshold: float = Field(default=0.50, gt=0, le=1)

    def require_google_configuration(self) -> None:
        """Fail early when an apply run is missing required credentials."""

        if not self.spreadsheet_id:
            raise ValueError("INVOICE_OPS_SPREADSHEET_ID is required with --apply")
        if not self.google_credentials_file.exists():
            raise ValueError(
                f"Google credentials not found: {self.google_credentials_file}"
            )
