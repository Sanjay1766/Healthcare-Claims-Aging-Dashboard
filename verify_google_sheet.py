from __future__ import annotations

import logging
from pathlib import Path

import gspread
from google.oauth2 import service_account
from gspread.exceptions import APIError, SpreadsheetNotFound


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

SPREADSHEET_ID = "1c6m8b_8a7liJZx0Am1suxbXeZnpVwHYB35FNStUQtE8"
SERVICE_ACCOUNT_FILE = "credentials/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _has_access_message(exception: Exception) -> str:
    message = str(exception)
    if isinstance(exception, SpreadsheetNotFound):
        return "Service account does not have access to the spreadsheet, or the spreadsheet ID is wrong."
    if isinstance(exception, APIError):
        status = getattr(getattr(exception, "response", None), "status_code", None)
        if status == 403:
            return "Service account does not have access to the spreadsheet."
        if status == 404:
            return "Spreadsheet was not found for this service account."
    if "403" in message:
        return "Service account does not have access to the spreadsheet."
    if "404" in message:
        return "Spreadsheet was not found for this service account."
    return "Access status could not be determined from the exception."


def main() -> None:
    credentials_path = Path(SERVICE_ACCOUNT_FILE)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Service account file not found: {credentials_path}")
    if credentials_path.stat().st_size == 0:
        raise ValueError(f"Service account file is empty: {credentials_path}")

    credentials = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=SCOPES
    )
    try:
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        print(f"Spreadsheet title: {spreadsheet.title}")
        print("Worksheet names:")

        for worksheet in spreadsheet.worksheets():
            print(f"- {worksheet.title}")

        print("Row counts per worksheet:")
        for worksheet in spreadsheet.worksheets():
            values = worksheet.get_all_values()
            data_rows = values[1:] if len(values) > 1 else []
            row_count = sum(1 for row in data_rows if any(cell not in (None, "") for cell in row))
            print(f"- {worksheet.title}: {row_count}")

    except Exception as exc:
        LOGGER.error("Google Sheets verification failed: %s", exc)
        print(f"Exact exception: {exc!r}")
        print(f"Access check: {_has_access_message(exc)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
