from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cleaning import clean_claim_data
from metrics import (
    calculate_aging_summary,
    calculate_employee_productivity,
    calculate_topline_metrics,
)


@dataclass(frozen=True)
class HistoricalTrendData:
    snapshot_summary: pd.DataFrame
    aging_distribution: pd.DataFrame
    ordered_sheet_names: list[str]
    latest_sheet_name: str | None


def parse_snapshot_date(sheet_name: str) -> pd.Timestamp:
    return pd.to_datetime(sheet_name, errors="coerce")


def build_historical_trend_data(workbook: dict[str, pd.DataFrame]) -> HistoricalTrendData:
    snapshot_rows: list[dict[str, object]] = []
    aging_frames: list[pd.DataFrame] = []

    ordered_sheets = [
        (parse_snapshot_date(sheet_name), sheet_name, raw_df)
        for sheet_name, raw_df in workbook.items()
    ]
    ordered_sheets = [item for item in ordered_sheets if pd.notna(item[0])]
    ordered_sheets.sort(key=lambda item: item[0], reverse=True)

    for snapshot_date, sheet_name, raw_df in ordered_sheets:
        cleaned_df = clean_claim_data(raw_df)
        topline_df = calculate_topline_metrics(cleaned_df)
        topline_map = topline_df.set_index("metric")["value"].to_dict() if not topline_df.empty else {}
        productivity_df = calculate_employee_productivity(cleaned_df)
        aging_summary_df = calculate_aging_summary(cleaned_df)

        snapshot_rows.append(
            {
                "snapshot_date": snapshot_date,
                "sheet_name": sheet_name,
                "snapshot_label": snapshot_date.strftime("%Y-%m-%d"),
                "total_claims": topline_map.get("Total Claims", len(cleaned_df)),
                "open_claims": topline_map.get("Open Claims", 0),
                "outstanding_balance": topline_map.get("Total Outstanding Balance", 0),
                "claims_worked": int(productivity_df["total_touches"].sum()) if not productivity_df.empty else 0,
                "dollars_recovered": topline_map.get("Total Balance Reductions", 0),
            }
        )

        if not aging_summary_df.empty:
            aging_summary_df = aging_summary_df.copy()
            aging_summary_df["snapshot_date"] = snapshot_date
            aging_summary_df["snapshot_label"] = snapshot_date.strftime("%Y-%m-%d")
            aging_summary_df["sheet_name"] = sheet_name
            aging_frames.append(aging_summary_df)

    snapshot_summary = pd.DataFrame(snapshot_rows)
    if not snapshot_summary.empty:
        snapshot_summary = snapshot_summary.sort_values("snapshot_date").reset_index(drop=True)

    aging_distribution = pd.concat(aging_frames, ignore_index=True) if aging_frames else pd.DataFrame(
        columns=["aging_bucket", "claim_count", "outstanding_balance", "percentage_of_total_balance", "snapshot_date", "sheet_name"]
    )

    ordered_sheet_names = [row[1] for row in ordered_sheets]
    latest_sheet_name = ordered_sheet_names[0] if ordered_sheet_names else None

    return HistoricalTrendData(
        snapshot_summary=snapshot_summary,
        aging_distribution=aging_distribution,
        ordered_sheet_names=ordered_sheet_names,
        latest_sheet_name=latest_sheet_name,
    )
