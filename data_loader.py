from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict

import pandas as pd


LOGGER = logging.getLogger(__name__)


def standardize_column_name(column_name: object) -> str:
    normalized = str(column_name).strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def load_excel_file(file_path: str) -> Dict[str, pd.DataFrame]:
    excel_path = Path(file_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    try:
        workbook = pd.ExcelFile(excel_path)
    except Exception as exc:
        LOGGER.exception("Failed to open Excel workbook")
        raise RuntimeError(f"Unable to read workbook: {excel_path.name}") from exc

    sheets: Dict[str, pd.DataFrame] = {}
    for sheet_name in workbook.sheet_names:
        try:
            frame = workbook.parse(sheet_name)
            if not frame.empty:
                frame.columns = [standardize_column_name(column) for column in frame.columns]
            sheets[sheet_name] = frame
        except Exception:
            LOGGER.exception("Failed to parse sheet %s", sheet_name)

    if not sheets:
        raise ValueError(f"No readable sheets were found in {excel_path.name}")

    return sheets
