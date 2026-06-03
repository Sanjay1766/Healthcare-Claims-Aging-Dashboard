from __future__ import annotations

import re

import pandas as pd


AGING_BUCKET_ORDER = ["0-30", "31-45", "46-60", "60+"]


def normalize_aging_bucket(value: object) -> object:
    if pd.isna(value):
        return pd.NA

    text = str(value).strip().lower()
    text = text.replace("days", "")

    bucket_patterns = {
        "0-30": [r"0\s*[-_]?\s*30", r"0\s*to\s*30"],
        "31-45": [r"31\s*[-_]?\s*45", r"31\s*to\s*45"],
        "46-60": [r"46\s*[-_]?\s*60", r"46\s*to\s*60"],
        "60+": [r"60\s*\+", r"60\s*plus", r"60\s*over"],
    }

    for bucket_name, patterns in bucket_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return bucket_name

    text = re.sub(r"\s+", "", text)
    text = text.replace("to", "-")
    text = text.replace("plus", "+")

    if text in {"0-30", "0_30", "0to30", "030"}:
        return "0-30"
    if text in {"31-45", "31_45", "31to45", "3145"}:
        return "31-45"
    if text in {"46-60", "46_60", "46to60", "4660"}:
        return "46-60"
    if text in {"60+", "60plus", "60over", "60"}:
        return "60+"
    return value


def _column_matches(column: str, candidates: list[str]) -> bool:
    return any(candidate in column for candidate in candidates)


def clean_claim_data(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    cleaned = df.copy().drop_duplicates().reset_index(drop=True)

    for column in cleaned.columns:
        if _column_matches(column, ["report_worked_date", "submission_date", "resubmission_date"]):
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")

    for column in cleaned.columns:
        if _column_matches(column, ["balance", "amount", "recovered", "collected", "paid", "charge"]) and not _column_matches(column, ["aging_bucket", "aging", "bucket"]):
            cleaned[column] = pd.to_numeric(
                cleaned[column].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"
            ).fillna(0)

    for column in cleaned.columns:
        if _column_matches(column, ["aging_bucket", "aging", "bucket"]):
            cleaned[column] = cleaned[column].map(normalize_aging_bucket)

    return cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
