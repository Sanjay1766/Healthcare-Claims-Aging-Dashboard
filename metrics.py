from __future__ import annotations

import pandas as pd

from cleaning import AGING_BUCKET_ORDER


AGING_BUCKET_CANDIDATES = ["claim_balance_aging", "pm_chasing", "aging_bucket", "aging", "bucket"]
WORKED_BY_CANDIDATES = ["report_worked_by", "worked_by", "employee", "assigned_to", "owner"]
CLAIM_ID_CANDIDATES = ["claim_id", "claim_number", "claim_no", "id"]
BALANCE_CANDIDATES = ["claim_balance", "outstanding_balance", "balance", "open_balance"]
RECOVERED_CANDIDATES = ["recovered_amount", "dollars_recovered", "collected_amount"]


def _resolve_column(df: pd.DataFrame, candidates: list[str], required: bool = True) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    if required:
        raise KeyError(f"Missing required column. Expected one of: {', '.join(candidates)}")
    return None


STATUS_CANDIDATES = ["claim_status", "status"]


def resolve_aging_bucket_column(df: pd.DataFrame) -> str | None:
    return _resolve_column(df, AGING_BUCKET_CANDIDATES, required=False)


def resolve_worked_by_column(df: pd.DataFrame) -> str | None:
    return _resolve_column(df, WORKED_BY_CANDIDATES, required=False)


def resolve_claim_status_column(df: pd.DataFrame) -> str | None:
    return _resolve_column(df, STATUS_CANDIDATES, required=False)


def _to_numeric_series(df: pd.DataFrame, column_name: str | None) -> pd.Series:
    if column_name is None:
        return pd.Series(0, index=df.index, dtype="float64")
    return pd.to_numeric(df[column_name], errors="coerce").fillna(0)


def _derive_recovered_amount(df: pd.DataFrame) -> pd.Series:
    recovered_column = _resolve_column(df, RECOVERED_CANDIDATES, required=False)
    if recovered_column:
        return _to_numeric_series(df, recovered_column)

    claim_amount_column = _resolve_column(df, ["claim_amount", "amount", "total_amount"], required=False)
    claim_balance_column = _resolve_column(df, BALANCE_CANDIDATES, required=False)
    if claim_amount_column and claim_balance_column:
        claim_amount = _to_numeric_series(df, claim_amount_column)
        claim_balance = _to_numeric_series(df, claim_balance_column)
        return (claim_amount - claim_balance).clip(lower=0)

    return pd.Series(0, index=df.index, dtype="float64")


def _bucket_sort(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    result = frame.copy()
    result[column] = pd.Categorical(result[column], categories=AGING_BUCKET_ORDER, ordered=True)
    return result.sort_values(column).reset_index(drop=True)


def calculate_topline_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["metric", "value"])

    balance_col = _resolve_column(df, BALANCE_CANDIDATES)
    recovered_series = _derive_recovered_amount(df)
    balance_series = _to_numeric_series(df, balance_col)

    open_claims = int((balance_series > 0).sum())
    closed_claims = int((balance_series <= 0).sum())
    total_outstanding = float(balance_series.sum())
    total_collected = float(recovered_series.sum())

    return pd.DataFrame(
        [
            {"metric": "Total Claims", "value": len(df)},
            {"metric": "Open Claims", "value": open_claims},
            {"metric": "Closed Claims", "value": closed_claims},
            {"metric": "Total Outstanding Balance", "value": total_outstanding},
            {"metric": "Total Balance Reductions", "value": total_collected},
        ]
    )


def calculate_aging_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["aging_bucket", "claim_count", "done_count", "outstanding_balance", "percentage_of_total_balance", "recovered_amount", "total_claimed"])

    aging_col = _resolve_column(df, AGING_BUCKET_CANDIDATES)
    balance_col = _resolve_column(df, BALANCE_CANDIDATES)

    # Derive recovered amount per claim
    recovered_series = _derive_recovered_amount(df)
    temp_df = df.copy()
    temp_df["_recovered"] = recovered_series
    temp_df["_is_done"] = temp_df[balance_col] <= 0

    summary = (
        temp_df.groupby(aging_col, dropna=False)
        .agg(
            claim_count=(aging_col, "size"),
            done_count=("_is_done", "sum"),
            outstanding_balance=(balance_col, "sum"),
            recovered_amount=("_recovered", "sum")
        )
        .reset_index()
        .rename(columns={aging_col: "aging_bucket"})
    )
    # Total = recovered + outstanding
    summary["total_claimed"] = summary["recovered_amount"] + summary["outstanding_balance"]
    
    total_balance = float(summary["outstanding_balance"].sum()) or 1.0
    summary["percentage_of_total_balance"] = summary["outstanding_balance"] / total_balance * 100
    return _bucket_sort(summary, "aging_bucket")


def calculate_employee_productivity(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["worked_by", "unique_claims_touched", "total_touches", "average_touches_per_claim"])

    worked_by_col = _resolve_column(df, WORKED_BY_CANDIDATES)
    claim_id_col = _resolve_column(df, CLAIM_ID_CANDIDATES, required=False)

    working = df.copy()
    if claim_id_col is None:
        working["_claim_id"] = working.index.astype(str)
        claim_id_col = "_claim_id"

    productivity = (
        working.groupby(worked_by_col)
        .agg(unique_claims_touched=(claim_id_col, "nunique"), total_touches=(claim_id_col, "size"))
        .reset_index()
        .rename(columns={worked_by_col: "worked_by"})
    )
    productivity["average_touches_per_claim"] = (
        productivity["total_touches"] / productivity["unique_claims_touched"].replace(0, pd.NA)
    )
    return productivity.fillna(0)


def calculate_aging_worked(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["worked_by", "aging_bucket", "touches"])

    worked_by_col = _resolve_column(df, WORKED_BY_CANDIDATES)
    aging_col = _resolve_column(df, AGING_BUCKET_CANDIDATES)

    return (
        df.groupby([worked_by_col, aging_col], dropna=False)
        .size()
        .reset_index(name="touches")
        .rename(columns={worked_by_col: "worked_by", aging_col: "aging_bucket"})
    )


def calculate_collection_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["aging_bucket", "recovered_amount", "outstanding_balance", "recovery_percentage"])

    recovered_series = _derive_recovered_amount(df)
    balance_col = _resolve_column(df, BALANCE_CANDIDATES)
    aging_col = _resolve_column(df, AGING_BUCKET_CANDIDATES)

    summary = (
        df.assign(_recovered_amount=recovered_series)
        .groupby(aging_col, dropna=False)
        .agg(recovered_amount=("_recovered_amount", "sum"), outstanding_balance=(balance_col, "sum"))
        .reset_index()
        .rename(columns={aging_col: "aging_bucket"})
    )
    summary["recovery_percentage"] = summary["recovered_amount"] / summary["outstanding_balance"].replace(0, pd.NA) * 100
    summary["recovery_percentage"] = summary["recovery_percentage"].fillna(0)
    return _bucket_sort(summary, "aging_bucket")


def calculate_employee_collection(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["worked_by", "recovered_amount"])

    worked_by_col = _resolve_column(df, WORKED_BY_CANDIDATES)
    recovered_series = _derive_recovered_amount(df)

    return (
        df.assign(_recovered_amount=recovered_series)
        .groupby(worked_by_col, dropna=False)
        .agg(recovered_amount=("_recovered_amount", "sum"))
        .reset_index()
        .rename(columns={worked_by_col: "worked_by"})
        .sort_values("recovered_amount", ascending=False)
        .reset_index(drop=True)
    )


def calculate_claims_done_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["aging_bucket", "done_count", "recovered_amount"])

    aging_col = _resolve_column(df, AGING_BUCKET_CANDIDATES)
    balance_col = _resolve_column(df, BALANCE_CANDIDATES)
    recovered_series = _derive_recovered_amount(df)

    temp_df = df.copy()
    temp_df["_recovered"] = recovered_series
    temp_df["_is_done"] = temp_df[balance_col] <= 0

    summary = (
        temp_df.groupby(aging_col, dropna=False)
        .agg(
            done_count=("_is_done", "sum"),
            recovered_amount=("_recovered", "sum")
        )
        .reset_index()
        .rename(columns={aging_col: "aging_bucket"})
    )
    return _bucket_sort(summary, "aging_bucket")
