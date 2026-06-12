from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

from data_loader import standardize_column_name


LOGGER = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_API_ROOT = "https://sheets.googleapis.com/v4/spreadsheets"


def _build_sheets_service(credentials_path: str):
    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        raise FileNotFoundError(f"Service account file not found: {credentials_file}")

    credentials = service_account.Credentials.from_service_account_file(
        str(credentials_file), scopes=SCOPES
    )
    return credentials


def _authorized_json_get(credentials, url: str) -> dict:
    if not credentials.valid or credentials.expired:
        credentials.refresh(GoogleAuthRequest())

    request = Request(url, headers={"Authorization": f"Bearer {credentials.token}"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _values_to_dataframe(values: list[list[object]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    header = [standardize_column_name(column) for column in values[0]]
    max_cols = max(len(row) for row in values)
    if len(header) < max_cols:
        header = header + [f"column_{i}" for i in range(len(header), max_cols)]
    header = [name if name else f"column_{i}" for i, name in enumerate(header)]

    rows = values[1:] if len(values) > 1 else []
    padded_rows = []
    for row in rows:
        if len(row) < len(header):
            row = list(row) + [None] * (len(header) - len(row))
        elif len(row) > len(header):
            row = list(row)[:len(header)]
        padded_rows.append(row)

    frame = pd.DataFrame(padded_rows, columns=header)
    return frame


def load_spreadsheet_workbook(
    spreadsheet_id: str,
    credentials_path: str = "credentials/service_account.json",
) -> Dict[str, pd.DataFrame]:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")

    credentials = _build_sheets_service(credentials_path)
    metadata_url = f"{SPREADSHEET_API_ROOT}/{spreadsheet_id}?fields=properties.title,sheets.properties.title"
    metadata = _authorized_json_get(credentials, metadata_url)

    sheets = metadata.get("sheets", [])
    workbook: Dict[str, pd.DataFrame] = {}
    for sheet in sheets:
        sheet_title = sheet["properties"]["title"]
        encoded_range = quote(sheet_title, safe="")
        values_url = f"{SPREADSHEET_API_ROOT}/{spreadsheet_id}/values/{encoded_range}"
        response = _authorized_json_get(credentials, values_url)
        values = response.get("values", [])
        workbook[sheet_title] = _values_to_dataframe(values)

    if not workbook:
        raise ValueError("No worksheets were returned by the spreadsheet")

    return workbook


def verify_sheet_row_counts(
    spreadsheet_id: str,
    credentials_path: str = "credentials/service_account.json",
) -> dict[str, object]:
    credentials = _build_sheets_service(credentials_path)
    metadata_url = f"{SPREADSHEET_API_ROOT}/{spreadsheet_id}?fields=properties.title,sheets.properties.title"
    metadata = _authorized_json_get(credentials, metadata_url)
    title = metadata.get("properties", {}).get("title", "")
    worksheets = []
    row_counts: dict[str, int] = {}

    for sheet in metadata.get("sheets", []):
        sheet_title = sheet["properties"]["title"]
        worksheets.append(sheet_title)
        encoded_range = quote(sheet_title, safe="")
        values_url = f"{SPREADSHEET_API_ROOT}/{spreadsheet_id}/values/{encoded_range}"
        response = _authorized_json_get(credentials, values_url)
        values = response.get("values", [])
        data_rows = values[1:] if len(values) > 1 else []
        row_counts[sheet_title] = sum(
            1 for row in data_rows if any(cell not in (None, "") for cell in row)
        )

    return {"title": title, "worksheets": worksheets, "row_counts": row_counts}
