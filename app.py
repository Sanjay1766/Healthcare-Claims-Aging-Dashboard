from __future__ import annotations

from datetime import datetime
from io import BytesIO
import logging
import os

import pandas as pd
import streamlit as st

import importlib
import cleaning
import metrics
import charts
import trend_analysis

# Hot-reload modules on rerun
importlib.reload(cleaning)
importlib.reload(metrics)
importlib.reload(charts)
importlib.reload(trend_analysis)

from charts import (
    aging_bucket_distribution,
    aging_bucket_trend,
    claims_done_distribution,
    claims_trend_over_time,
    claims_worked_by_employee,
    claims_worked_trend,
    collection_amount_by_bucket,
    collection_amount_by_employee,
    outstanding_balance_by_bucket,
    outstanding_balance_trend,
    recovery_trend,
    worked_vs_recovered,
    snapshot_progression_trend,
    follow_up_frequency_chart,
    employee_follow_up_chart,
    executive_productivity_trend_chart,
)
from cleaning import clean_claim_data, normalize_aging_bucket
from google_sheets_connector import load_spreadsheet_workbook
from trend_analysis import build_historical_trend_data
from metrics import (
    calculate_aging_summary,
    calculate_aging_worked,
    calculate_claims_done_summary,
    calculate_collection_summary,
    calculate_employee_collection,
    calculate_employee_productivity,
    calculate_topline_metrics,
    resolve_aging_bucket_column,
    resolve_claim_status_column,
    resolve_worked_by_column,
)

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None


logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="Healthcare Claims Aging Dashboard", layout="wide")

# Injecting Premium Sleek Custom Stylesheet
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* Main App Container */
.stApp {
    background-color: #030712 !important;
    background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.08) 0px, transparent 50%) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #f1f5f9 !important;
}

/* Adjust top padding to pull layout upwards safely without cutting off */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 2rem !important;
}

/* Transparent Streamlit Header & Top Decoration */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    background: transparent !important;
}
div[data-testid="stDecoration"] {
    background: linear-gradient(90deg, #06b6d4, #6366f1) !important;
}

/* Make custom component iframes and containers transparent */
iframe {
    background-color: transparent !important;
    background: transparent !important;
}
div[data-testid="stCustomComponentV1"] {
    background-color: transparent !important;
    background: transparent !important;
}

/* Custom Scrollbars */
::-webkit-scrollbar {
    width: 6px !important;
    height: 6px !important;
}
::-webkit-scrollbar-track {
    background: #030712 !important;
}
::-webkit-scrollbar-thumb {
    background: #1e293b !important;
    border-radius: 10px !important;
}
::-webkit-scrollbar-thumb:hover {
    background: #334155 !important;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090d16 0%, #030712 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
    color: #9ca3af !important;
    font-size: 14px !important;
}
section[data-testid="stSidebar"] h2 {
    color: #06b6d4 !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

/* Sidebar Radio Selector */
div[data-testid="stRadio"] > label {
    font-weight: 600 !important;
    color: #e5e7eb !important;
    font-size: 14px !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    background-color: rgba(30, 41, 59, 0.3) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin-bottom: 10px !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100% !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background-color: rgba(30, 41, 59, 0.65) !important;
    border-color: rgba(6, 182, 212, 0.4) !important;
    transform: translateX(4px) !important;
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.1) !important;
    cursor: pointer !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] div {
    color: #ffffff !important;
    font-weight: 600 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] div[data-testid="stMarker"] {
    border-color: #06b6d4 !important;
    background-color: #06b6d4 !important;
}

/* Main Dashboard Header */
.main-header {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 30px !important;
    margin-bottom: 35px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important;
    position: relative !important;
    overflow: hidden !important;
}
.main-header::before {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 3px !important;
    background: linear-gradient(90deg, #06b6d4 0%, #6366f1 50%, #a855f7 100%) !important;
}

/* Metric Cards styling */
div[data-testid="metric-container"] {
    background: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 18px !important;
    padding: 20px 12px !important;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-4px) !important;
    border-color: rgba(6, 182, 212, 0.4) !important;
    box-shadow: 0 20px 30px rgba(0, 0, 0, 0.4), 0 0 20px rgba(6, 182, 212, 0.15) !important;
}
div[data-testid="metric-container"]::before {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 3px !important;
    background: linear-gradient(90deg, #06b6d4 0%, #6366f1 100%) !important;
}

/* Metric Value and Label */
div[data-testid="stMetricValue"] > div {
    font-size: 22px !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    letter-spacing: -0.5px !important;
    background: linear-gradient(135deg, #ffffff 60%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
div[data-testid="stMetricLabel"] > div {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    margin-bottom: 6px !important;
}

/* Streamlit Native Selectbox & Inputs override */
div[data-baseweb="select"] > div {
    background-color: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    padding: 2px 4px !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    transition: all 0.2s ease-in-out !important;
}
div[data-baseweb="select"] > div:hover {
    border-color: #06b6d4 !important;
    box-shadow: 0 0 10px rgba(6, 182, 212, 0.1) !important;
}

/* Dataframe & Tables styling */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2) !important;
    background-color: #0f172a !important;
}

/* Info and Warning Alerts */
div[data-testid="stNotification"] {
    background-color: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    color: #f1f5f9 !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2) !important;
}

/* Plotly Chart container styling */
div[class="stPlotlyChart"] {
    background-color: rgba(15, 23, 42, 0.4) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25) !important;
    margin-bottom: 30px !important;
    transition: all 0.3s ease !important;
}
div[class="stPlotlyChart"]:hover {
    border-color: rgba(255, 255, 255, 0.12) !important;
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35) !important;
}

/* Download Buttons styling */
.stDownloadButton button,
button[data-testid="baseButton-secondary"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #06b6d4 !important;
    border: 1px solid rgba(6, 182, 212, 0.4) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
}
.stDownloadButton button:hover,
button[data-testid="baseButton-secondary"]:hover {
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%) !important;
    color: #ffffff !important;
    border-color: #06b6d4 !important;
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.4) !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton button p,
.stDownloadButton button span,
button[data-testid="baseButton-secondary"] p,
button[data-testid="baseButton-secondary"] span {
    color: inherit !important;
    font-weight: 600 !important;
}

/* Custom Chat Input Styling - Centered and Clean like ChatGPT */
div[data-testid="stChatInput"] {
    max-width: 768px !important;
    margin: 0 auto !important;
    background-color: #0f172a !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}
div[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: #ffffff !important;
    border: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.95rem !important;
}
div[data-testid="stChatInput"] button {
    background-color: #06b6d4 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
}
div[data-testid="stChatInput"] button:hover {
    background-color: #0891b2 !important;
}

/* Smooth fade-in animation for chat messages */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Pulse animation for the typing indicator */
@keyframes pulse {
    0%, 100% {
        transform: scale(0.8);
        opacity: 0.4;
    }
    50% {
        transform: scale(1.2);
        opacity: 1;
    }
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# Select the page first so we can conditionally render components
page = st.sidebar.radio(
    "Page",
    ["Executive Summary", "Productivity Analysis", "Historical Trends", "Snapshot Progression", "Follow-up Analysis", "AI Chat"],
)

# Centered Header styling and text (hidden on AI Chat page)
if page != "AI Chat":
    st.markdown(
        """
        <div style="text-align: center; margin-top: 0px; margin-bottom: 20px;">
            <h1 style="font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 40%, #a5f3fc 70%, #c084fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.5px;">
                Healthcare Accounts Receivable & Claims Aging Dashboard
            </h1>
            <p style="font-size: 1.05rem; color: #94a3b8; max-width: 900px; margin: 0 auto; font-family: 'Plus Jakarta Sans', sans-serif; line-height: 1.5; font-weight: 400;">
                Enterprise financial analytics platform for tracking claims status, employee productivity, and balance recovery trends.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


SPREADSHEET_ID = "1c6m8b_8a7liJZx0Am1suxbXeZnpVwHYB35FNStUQtE8"


@st.cache_data(show_spinner=False)
def load_source_data(spreadsheet_id: str, credentials_path: str):
    return load_spreadsheet_workbook(spreadsheet_id, credentials_path=credentials_path)


def _first_existing_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _normalize_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _apply_filters(
    frame: pd.DataFrame,
    aging_column: str | None,
    selected_aging: list[str],
    employee_column: str | None,
    selected_employees: list[str],
    status_column: str | None,
    selected_statuses: list[str],
    date_column: str | None,
    selected_dates: tuple | None,
) -> pd.DataFrame:
    filtered = frame.copy()

    if aging_column and selected_aging:
        filtered = filtered[
            filtered[aging_column].map(normalize_aging_bucket).astype(str).isin(selected_aging)
        ]

    if employee_column and selected_employees:
        emp_series = filtered[employee_column].fillna("Unassigned").astype(str)
        filtered = filtered[emp_series.isin(selected_employees)]

    if status_column and selected_statuses:
        status_series = filtered[status_column].fillna("Blank").astype(str)
        filtered = filtered[status_series.isin(selected_statuses)]

    if date_column and isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        date_series = _normalize_date_series(filtered[date_column])
        filtered = filtered[(date_series.dt.date >= start_date) & (date_series.dt.date <= end_date)]

    return filtered


def _build_excel_export(sheets_map: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets_map.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer.seek(0)
    return buffer.read()


def _download_pair(title: str, dataframe: pd.DataFrame, file_stem: str) -> None:
    left, right = st.columns(2)
    with left:
        st.download_button(
            f"Download {title} CSV",
            dataframe.to_csv(index=False).encode("utf-8"),
            file_name=f"{file_stem}.csv",
            mime="text/csv",
        )
    with right:
        st.download_button(
            f"Download {title} Excel",
            _build_excel_export({title: dataframe}),
            file_name=f"{file_stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", SPREADSHEET_ID)
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials/service_account.json")

if st_autorefresh is not None:
    st_autorefresh(interval=30 * 60 * 1000, key="claims_dashboard_refresh")

if not spreadsheet_id:
    st.info("Enter the Google Spreadsheet ID when the API link is ready. The analytics layer is scaffolded already.")
    st.stop()

try:
    sheets = load_source_data(spreadsheet_id, credentials_path)
    if page != "AI Chat":
        st.caption(f"Connected spreadsheet: {spreadsheet_id}")
except Exception as exc:
    st.error(f"Unable to load source data: {exc}")
    st.stop()

cleaned_sheets = {
    sheet_name: clean_claim_data(sheet_df)
    for sheet_name, sheet_df in sheets.items()
    if pd.notna(pd.to_datetime(sheet_name, errors="coerce"))
}
all_cleaned_rows = pd.concat(cleaned_sheets.values(), ignore_index=True) if cleaned_sheets else pd.DataFrame()

aging_column_for_filters = resolve_aging_bucket_column(all_cleaned_rows)
employee_column_for_filters = resolve_worked_by_column(all_cleaned_rows)
status_column_for_filters = resolve_claim_status_column(all_cleaned_rows)
date_column_for_filters = _first_existing_column(
    all_cleaned_rows,
    ["submission_date", "report_worked_date", "date_of_service", "resubmission_date"],
)

if date_column_for_filters is not None and not all_cleaned_rows.empty:
    date_series = _normalize_date_series(all_cleaned_rows[date_column_for_filters])
    valid_dates = date_series.dropna()
    min_date = valid_dates.min().date() if not valid_dates.empty else None
    max_date = valid_dates.max().date() if not valid_dates.empty else None
else:
    min_date = None
    max_date = None

# Set up selections internally without displaying filter inputs in the UI sidebar
aging_options: list[str] = []
if aging_column_for_filters:
    aging_options = sorted(
        {str(normalize_aging_bucket(value)) for value in all_cleaned_rows[aging_column_for_filters].dropna().tolist()}
    )
selected_aging_buckets = aging_options

employee_options: list[str] = []
if employee_column_for_filters:
    employee_options = sorted(all_cleaned_rows[employee_column_for_filters].fillna("Unassigned").astype(str).unique().tolist())
selected_employees = employee_options

status_options: list[str] = []
if status_column_for_filters:
    status_options = sorted(all_cleaned_rows[status_column_for_filters].fillna("Blank").astype(str).unique().tolist())
selected_statuses = status_options

selected_date_range = (min_date, max_date) if min_date is not None and max_date is not None else None

dashboard_filters = {
    "aging_bucket": selected_aging_buckets,
    "employee": selected_employees,
    "claim_status": selected_statuses,
    "date_range": selected_date_range if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2 else None,
}

filtered_sheets = {
    sheet_name: _apply_filters(
        sheet_df,
        aging_column_for_filters,
        selected_aging_buckets,
        employee_column_for_filters,
        selected_employees,
        status_column_for_filters,
        selected_statuses,
        date_column_for_filters,
        dashboard_filters["date_range"],
    )
    for sheet_name, sheet_df in cleaned_sheets.items()
}

historical_data = build_historical_trend_data(filtered_sheets)
sheet_options = historical_data.ordered_sheet_names or list(filtered_sheets.keys())

if not sheet_options:
    st.warning("No worksheets were available after filtering.")
    st.stop()

latest_sheet = historical_data.latest_sheet_name or sheet_options[-1]

# Create logical datasets and calculate corresponding metrics
current_snapshot_df = filtered_sheets[latest_sheet] if latest_sheet in filtered_sheets else pd.DataFrame()
topline_current = calculate_topline_metrics(current_snapshot_df)
topline_current_map = topline_current.set_index("metric")["value"] if not topline_current.empty else pd.Series(dtype="object")

# Executive Summary visuals rely on the Current Snapshot Dataset
aging_summary_df = calculate_aging_summary(current_snapshot_df)
collection_summary_df = calculate_collection_summary(current_snapshot_df)
claims_done_df = calculate_claims_done_summary(current_snapshot_df)
employee_productivity_current_df = calculate_employee_productivity(current_snapshot_df)

# Assemble unique claim portfolio (Unique Claim Dataset)
portfolio_frames = []
for sheet_name, sheet_df in filtered_sheets.items():
    if not sheet_df.empty:
        df_copy = sheet_df.copy()
        df_copy["_snapshot_date"] = pd.to_datetime(sheet_name, errors="coerce")
        portfolio_frames.append(df_copy)
if portfolio_frames:
    combined_portfolio = pd.concat(portfolio_frames, ignore_index=True)
    combined_portfolio["composite_key"] = combined_portfolio["patient_id"].astype(str) + "_" + combined_portfolio["claim_id"].astype(str)
    unique_claim_df = combined_portfolio.sort_values("_snapshot_date").drop_duplicates(subset=["composite_key"], keep="last")
else:
    unique_claim_df = pd.DataFrame()

topline_unique = calculate_topline_metrics(unique_claim_df)
topline_unique_map = topline_unique.set_index("metric")["value"] if not topline_unique.empty else pd.Series(dtype="object")

# Operational Dataset consists of all worksheets combined (touches carry forward snapshot actions)
operational_df = pd.concat(filtered_sheets.values(), ignore_index=True) if filtered_sheets else pd.DataFrame()
employee_productivity_df = calculate_employee_productivity(operational_df)
aging_worked_df = calculate_aging_worked(operational_df)
employee_collection_df = calculate_employee_collection(operational_df)

last_refresh = st.session_state.get("last_refresh")
if last_refresh is None:
    last_refresh = datetime.now()
    st.session_state["last_refresh"] = last_refresh
if page != "AI Chat":
    st.caption(f"Last refresh: {last_refresh:%Y-%m-%d %H:%M:%S}")

def format_metric_value(val, is_currency=False):
    try:
        if hasattr(val, "item"):
            val = val.item()
        num = float(val)
        if is_currency:
            return f"${num:,.0f}"
        else:
            return f"{num:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def get_groq_response(user_prompt: str, current_metrics_context: str) -> str:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    import os
    groq_api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    
    # Truncate context to avoid token limit errors (must happen before building system_prompt)
    if len(current_metrics_context) > 3000:
        current_metrics_context = current_metrics_context[:3000] + "\n... [truncated]"

    system_prompt = f"""
    You are a professional Healthcare Accounts Receivable & Claims Assistant.
    You have access to the live dashboard metrics below:
    
    {current_metrics_context}
    
    Answer the user's questions clearly, concisely, and professionally using the metrics provided.
    Format your responses cleanly (bold key metrics, use bullet points for lists, etc.).
    Do not use emojis in your response. Do not add glittering effects.
    """
    
    payload = {
        "model": "qwen/qwen3.6-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 512,
        "reasoning_format": "hidden"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if not response.ok:
            return f"Unable to fetch response from AI Assistant: {response.status_code} - {response.text}"
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Unable to fetch response from AI Assistant: {str(e)}"


if page != "AI Chat":
    cols = st.columns(6)
    metrics = [
        ("Total Claims", topline_current_map.get("Total Claims", 0)),
        ("Open Claims", topline_current_map.get("Open Claims", 0)),
        ("Closed Claims", topline_current_map.get("Closed Claims", 0)),
        ("$ Outstanding Balance", topline_current_map.get("Total Outstanding Balance", 0)),
        ("$ Balance Reductions", topline_current_map.get("Total Balance Reductions", 0)),
        ("Claims Worked", int(employee_productivity_current_df["total_touches"].sum()) if not employee_productivity_current_df.empty else 0),
    ]
    for column, (label, value) in zip(cols, metrics):
        with column:
            is_currency = label in ["$ Outstanding Balance", "$ Balance Reductions"]
            st.metric(label, format_metric_value(value, is_currency=is_currency))

if page == "Executive Summary":
    st.plotly_chart(aging_bucket_distribution(aging_summary_df), use_container_width=True)
    st.plotly_chart(outstanding_balance_by_bucket(aging_summary_df), use_container_width=True)
    st.plotly_chart(claims_done_distribution(claims_done_df), use_container_width=True)
    st.dataframe(collection_summary_df, use_container_width=True)
    _download_pair("Aging Summary", aging_summary_df, "aging_summary")

elif page == "Productivity Analysis":
    st.plotly_chart(claims_worked_by_employee(employee_productivity_df), use_container_width=True)
    st.dataframe(aging_worked_df, use_container_width=True)
    st.dataframe(employee_productivity_df, use_container_width=True)
    _download_pair("Claims Worked Analysis", employee_productivity_df, "claims_worked_analysis")

elif page == "Historical Trends":
    if historical_data.snapshot_summary.empty:
        st.warning("No historical snapshot data is available.")
    else:
        # Get the summary data
        sorted_summary = historical_data.snapshot_summary.sort_values("snapshot_date").copy()
        
        # Filter to target dates
        target_dates = [
            pd.to_datetime("2026-05-04").date(),
            pd.to_datetime("2026-05-11").date(),
            pd.to_datetime("2026-05-18").date(),
            pd.to_datetime("2026-05-26").date(),
        ]
        sorted_summary["date_only"] = sorted_summary["snapshot_date"].dt.date
        sorted_summary = sorted_summary[sorted_summary["date_only"].isin(target_dates)].copy()
        
        if len(sorted_summary) < 4:
            st.warning("Ensure that worksheets for all 4 weeks of May 2026 (5/4/2026, 5/11/2026, 5/18/2026, 5/26/2026) are loaded.")
        else:
            # Sort chronologically to compute metrics
            sorted_summary = sorted_summary.sort_values("snapshot_date").reset_index(drop=True)
            
            # Slide Header (Title and Subtitle)
            st.markdown(
                """
                <div style="text-align: left; margin-top: 10px; margin-bottom: 25px;">
                    <h2 style="font-size: 2.2rem; font-weight: 800; color: #ffffff; font-family: 'Plus Jakarta Sans', sans-serif; margin-bottom: 5px;">
                        Monthly Productivity Trend
                    </h2>
                    <p style="font-size: 1.1rem; color: #94a3b8; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; font-weight: 400;">
                        Claims Inventory and Outstanding AR Progression &bull; May 2026
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Draw single dual-axis chart
            st.plotly_chart(executive_productivity_trend_chart(sorted_summary), use_container_width=True)
            
            # Executive Insight Section
            # Calculate values dynamically
            beg_row = sorted_summary.iloc[0]
            end_row = sorted_summary.iloc[-1]
            
            beg_claims = int(beg_row["total_claims"])
            end_claims = int(end_row["total_claims"])
            claims_diff = beg_claims - end_claims  # positive means reduction
            
            beg_ar = float(beg_row["outstanding_balance"])
            end_ar = float(end_row["outstanding_balance"])
            ar_diff = beg_ar - end_ar  # positive means reduction
            
            st.markdown(
                f"""
                <div style="background-color: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 18px; padding: 25px; margin-top: 10px;">
                    <h3 style="color: #ffffff; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.35rem; font-weight: 700; margin-top: 0; margin-bottom: 15px;">Executive Summary</h3>
                    <p style="color: #cbd5e1; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; line-height: 1.6; margin-bottom: 12px;">
                        Claims inventory decreased from <b>{beg_claims:,}</b> claims to <b>{end_claims:,}</b> claims during May 2026.
                    </p>
                    <p style="color: #cbd5e1; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; line-height: 1.6; margin-bottom: 20px;">
                        Outstanding AR decreased from <b>${beg_ar/1e6:.3f}M</b> to <b>${end_ar/1e6:.3f}M</b>.
                    </p>
                    <h4 style="color: #ffffff; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.05rem; font-weight: 600; margin-top: 0; margin-bottom: 10px;">Net Improvement:</h4>
                    <ul style="color: #cbd5e1; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; line-height: 1.6; margin-top: 0; margin-bottom: 20px; padding-left: 20px;">
                        <li><b>{claims_diff:,}</b> fewer claims in inventory</li>
                        <li><b>${ar_diff/1e3:.0f}K</b> reduction in outstanding receivables</li>
                    </ul>
                    <p style="color: #94a3b8; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0; font-style: italic;">
                        This indicates positive operational productivity and portfolio reduction over the reporting period.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

elif page == "Snapshot Progression":
    st.subheader("Beginning vs. End of Month Progression")
    if historical_data.snapshot_summary.empty:
        st.warning("No historical snapshot data is available.")
    else:
        # Sort chronologically to identify beginning and end of month
        sorted_summary = historical_data.snapshot_summary.sort_values("snapshot_date").reset_index(drop=True)
        beg_row = sorted_summary.iloc[0]
        end_row = sorted_summary.iloc[-1]
        
        st.markdown("### Executive Summary KPI Progression")
        col1, col2, col3 = st.columns(3)
        
        # AR Balance delta
        beg_ar = float(beg_row["outstanding_balance"])
        end_ar = float(end_row["outstanding_balance"])
        ar_diff = end_ar - beg_ar
        ar_pct = (ar_diff / beg_ar * 100) if beg_ar != 0 else 0
        with col1:
            st.metric(
                label="Outstanding AR Balance Progression",
                value=f"${end_ar:,.2f}",
                delta=f"${ar_diff:+,.2f} ({ar_pct:+.1f}%)",
                delta_color="inverse"
            )
            
        # Recovery/Collected delta
        beg_rec = float(beg_row["dollars_recovered"])
        end_rec = float(end_row["dollars_recovered"])
        rec_diff = end_rec - beg_rec
        rec_pct = (rec_diff / beg_rec * 100) if beg_rec != 0 else 0
        with col2:
            st.metric(
                label="Monthly Recovery Progression",
                value=f"${end_rec:,.2f}",
                delta=f"${rec_diff:+,.2f} ({rec_pct:+.1f}%)"
            )
            
        # Touches delta
        beg_tou = int(beg_row["claims_worked"])
        end_tou = int(end_row["claims_worked"])
        tou_diff = end_tou - beg_tou
        tou_pct = (tou_diff / beg_tou * 100) if beg_tou != 0 else 0
        with col3:
            st.metric(
                label="Weekly Touches Progression",
                value=f"{end_tou:,}",
                delta=f"{tou_diff:+,} ({tou_pct:+.1f}%)",
                delta_color="inverse"
            )
            
        st.markdown("---")
        st.markdown("### Weekly Snapshot Volume Deltas")
        col4, col5, col6 = st.columns(3)
        
        # Total Claims delta
        beg_claims = int(beg_row["total_claims"])
        end_claims = int(end_row["total_claims"])
        claims_diff = end_claims - beg_claims
        claims_pct = (claims_diff / beg_claims * 100) if beg_claims != 0 else 0
        with col4:
            st.metric(
                label="Total Claims",
                value=f"{end_claims:,}",
                delta=f"{claims_diff:+,} ({claims_pct:+.1f}%)",
                delta_color="inverse"
            )
            
        # Open Claims delta
        beg_open = int(beg_row["open_claims"])
        end_open = int(end_row["open_claims"])
        open_diff = end_open - beg_open
        open_pct = (open_diff / beg_open * 100) if beg_open != 0 else 0
        with col5:
            st.metric(
                label="Remaining Claims",
                value=f"{end_open:,}",
                delta=f"{open_diff:+,} ({open_pct:+.1f}%)",
                delta_color="inverse"
            )
            
        # Closed Claims delta
        beg_closed = beg_claims - beg_open
        end_closed = end_claims - end_open
        closed_diff = end_closed - beg_closed
        closed_pct = (closed_diff / beg_closed * 100) if beg_closed != 0 else 0
        with col6:
            st.metric(
                label="Closed Claim",
                value=f"{end_closed:,}",
                delta=f"{closed_diff:+,} ({closed_pct:+.1f}%)"
            )

        st.plotly_chart(snapshot_progression_trend(sorted_summary), use_container_width=True)
        
        st.markdown("### Raw Snapshot Progression Data")
        prog_df_display = sorted_summary.copy()
        prog_df_display = prog_df_display.rename(columns={
            "snapshot_label": "Snapshot Date",
            "total_claims": "Total Claims",
            "open_claims": "Open Claims",
            "outstanding_balance": "Outstanding AR ($)",
            "dollars_recovered": "Balance Reductions ($)",
            "claims_worked": "Touches"
        })
        st.dataframe(prog_df_display[["Snapshot Date", "Total Claims", "Open Claims", "Outstanding AR ($)", "Balance Reductions ($)", "Touches"]], use_container_width=True)
        _download_pair("Progression Analysis", prog_df_display, "progression_analysis")

elif page == "Follow-up Analysis":
    st.subheader("Denials Follow-up Frequency Analysis")
    
    # Combine all weekly worksheets
    frames_all = []
    for sheet_name, sheet_df in filtered_sheets.items():
        if not sheet_df.empty:
            df_copy = sheet_df.copy()
            df_copy["_sheet_name"] = sheet_name
            df_copy["_snapshot_date"] = pd.to_datetime(sheet_name, errors="coerce")
            frames_all.append(df_copy)
            
    if not frames_all:
        st.warning("No data is available for follow-up analysis.")
    else:
        combined_all = pd.concat(frames_all, ignore_index=True)
        combined_all["composite_key"] = combined_all["patient_id"].astype(str) + "_" + combined_all["claim_id"].astype(str)
        
        # Clean worked actions (non-null report_worked_by)
        worked_only = combined_all[combined_all["report_worked_by"].notna()].copy()
        
        if worked_only.empty:
            st.info("No claims have been worked in the active datasets.")
        else:
            # Group by composite key to find touch stats
            follow_stats = (
                worked_only.groupby("composite_key")
                .agg(
                    touch_count=("report_worked_by", "size"),
                    unique_workers=("report_worked_by", "nunique"),
                    worked_dates=("report_worked_date", "nunique"),
                    latest_status=("claim_status", "last"),
                    latest_balance=("claim_balance", "last"),
                    initial_balance=("claim_balance", "first"),
                    patient_id=("patient_id", "first"),
                    claim_id=("claim_id", "first"),
                    plan_name=("plan_name", "first"),
                    report_worked_by=("report_worked_by", "last")
                )
                .reset_index()
            )
            
            # Follow-up claims: touched > 1 time
            follow_stats["recovered_amount"] = (follow_stats["initial_balance"] - follow_stats["latest_balance"]).clip(lower=0)
            multi_touch_claims = follow_stats[follow_stats["touch_count"] > 1].copy()
            
            # Overview KPIs
            total_unique_worked = len(follow_stats)
            total_followed_up = len(multi_touch_claims)
            follow_up_rate = (total_followed_up / total_unique_worked * 100) if total_unique_worked > 0 else 0
            avg_touches_followup = multi_touch_claims["touch_count"].mean() if total_followed_up > 0 else 0
            total_recovered_followup = multi_touch_claims["recovered_amount"].sum()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Unique Claims Worked", f"{total_unique_worked:,}")
            with col2:
                st.metric("Claims Followed Up (>1 Touch)", f"{total_followed_up:,}", f"{follow_up_rate:.1f}% Follow-up Rate")
            with col3:
                st.metric("Avg Touches / Follow-up", f"{avg_touches_followup:.2f}")
            with col4:
                st.metric("AR Recovered via Follow-ups", f"${total_recovered_followup:,.2f}")
                
            st.markdown("---")
            
            # Charts
            freq_series = follow_stats["touch_count"].value_counts().reset_index()
            freq_series.columns = ["touch_count", "claim_count"]
            freq_series["touch_count"] = freq_series["touch_count"].astype(str) + "x"
            freq_series = freq_series.sort_values("touch_count")
            
            st.plotly_chart(follow_up_frequency_chart(freq_series), use_container_width=True)
                
            # Registry Table
            st.markdown("### Detailed Claims Follow-up Registry")
            st.markdown("Listing claims worked multiple times in the month with balance changes:")
            
            registry_display = multi_touch_claims.copy()
            registry_display = registry_display.rename(columns={
                "patient_id": "Patient ID",
                "claim_id": "Claim ID",
                "plan_name": "Plan Name",
                "touch_count": "Total Touches",
                "initial_balance": "Initial Balance ($)",
                "latest_balance": "Latest Balance ($)",
                "recovered_amount": "Recovered Amount ($)",
                "latest_status": "Latest Status",
                "report_worked_by": "Last Action By"
            })
            
            cols_to_show = [
                "Patient ID", "Claim ID", "Plan Name", "Total Touches", 
                "Initial Balance ($)", "Latest Balance ($)", "Recovered Amount ($)", 
                "Latest Status", "Last Action By"
            ]
            st.dataframe(registry_display[cols_to_show].sort_values("Total Touches", ascending=False), use_container_width=True)
            _download_pair("Claims Follow-up Registry", registry_display[cols_to_show], "claims_followup_registry")


elif page == "AI Chat":
    # Top-centered clean title block, no emoji, no glittering/neon line effects
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px; margin-bottom: 40px;">
            <h2 style="font-size: 2.2rem; font-weight: 700; color: #ffffff; font-family: 'Plus Jakarta Sans', sans-serif; margin-bottom: 10px; letter-spacing: -0.5px;">
                Agentic Reporting
            </h2>
            <p style="font-size: 1.05rem; color: #94a3b8; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0 auto; max-width: 600px; font-weight: 400; line-height: 1.5;">
                Interact with the AI Assistant to query live claims metrics, analyze aging buckets, and check employee recovery progress.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant", 
                "content": "Hello! I am your AI Claims Assistant. How can I help you analyze your accounts receivable, claims productivity, or collection trends today?"
            }
        ]

    # Display chat messages from history inside centered layout with no emoji or glitter
    for message in st.session_state["chat_messages"]:
        content_html = message["content"]
        
        # If the content is "loading", display a clean professional pulsing typing indicator
        if content_html == "loading":
            content_html = """
            <div style="display: flex; gap: 6px; align-items: center; height: 20px;">
                <span style="width: 6px; height: 6px; background-color: #94a3b8; border-radius: 50%; display: inline-block; animation: pulse 1.2s infinite ease-in-out;"></span>
                <span style="width: 6px; height: 6px; background-color: #94a3b8; border-radius: 50%; display: inline-block; animation: pulse 1.2s infinite ease-in-out; animation-delay: 0.2s;"></span>
                <span style="width: 6px; height: 6px; background-color: #94a3b8; border-radius: 50%; display: inline-block; animation: pulse 1.2s infinite ease-in-out; animation-delay: 0.4s;"></span>
            </div>
            """
        else:
            # Basic markdown bold parser (**text** -> <b>text</b>)
            import re
            content_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content_html)
            content_html = content_html.replace("\n", "<br>")

        if message["role"] == "user":
            st.markdown(
                f"""
                <div style="max-width: 768px; margin: 0 auto; display: flex; justify-content: flex-end; margin-bottom: 20px;">
                    <div style="background-color: #1e293b; 
                                border: 1px solid rgba(255, 255, 255, 0.08); 
                                border-radius: 12px; 
                                padding: 14px 18px; 
                                max-width: 80%; 
                                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); 
                                color: #f8fafc; 
                                font-family: 'Plus Jakarta Sans', sans-serif;
                                animation: fadeIn 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards;">
                        <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">You</div>
                        <div style="font-size: 0.98rem; line-height: 1.5; font-weight: 400;">{content_html}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="max-width: 768px; margin: 0 auto; display: flex; justify-content: flex-start; margin-bottom: 20px;">
                    <div style="background-color: #0f172a; 
                                border: 1px solid rgba(255, 255, 255, 0.08); 
                                border-radius: 12px; 
                                padding: 14px 18px; 
                                max-width: 80%; 
                                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); 
                                color: #e2e8f0; 
                                font-family: 'Plus Jakarta Sans', sans-serif;
                                animation: fadeIn 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards;">
                        <div style="font-size: 0.75rem; color: #06b6d4; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">AI Claims Assistant</div>
                        <div style="font-size: 0.98rem; line-height: 1.5; font-weight: 400;">{content_html}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # React to user input
    if prompt := st.chat_input("Ask a question about your claims dashboard data..."):
        # Add user message and a placeholder loading assistant bubble to history
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        st.session_state["chat_messages"].append({"role": "assistant", "content": "loading"})
        st.rerun()

    # Check if there is a pending response generation
    if (
        st.session_state["chat_messages"] 
        and st.session_state["chat_messages"][-1]["role"] == "assistant" 
        and st.session_state["chat_messages"][-1]["content"] == "loading"
    ):
        user_prompt = st.session_state["chat_messages"][-2]["content"]
        
        # Compile live metrics context to give Groq detailed environment info using our database logic
        topline_str = topline_current_map.to_string() if not topline_current_map.empty else "No topline data available"
        aging_str = aging_summary_df.to_string(index=False) if not aging_summary_df.empty else "No aging bucket data available"
        productivity_str = employee_productivity_df.to_string(index=False) if not employee_productivity_df.empty else "No employee productivity data available"
        collection_str = collection_summary_df.to_string(index=False) if not collection_summary_df.empty else "No collection summary data available"
        
        context_str = f"""
        Active Sheet (Snapshot Date): {latest_sheet}
        
        --- OVERALL DASHBOARD FINANCIAL KPIs ---
        {topline_str}
        
        --- AR AGING BUCKETS DISTRIBUTION (OUR AGING LOGIC) ---
        {aging_str}
        
        --- EMPLOYEE PRODUCTIVITY ANALYSIS (OUR touches AND completed_claims LOGIC) ---
        {productivity_str}
        
        --- BALANCES & COLLECTION SUMMARY (OUR recovery_rate LOGIC) ---
        {collection_str}
        """
        
        # Call Groq LLM API
        response = get_groq_response(user_prompt, context_str)

        # Update the placeholder message with the final response and refresh the page
        st.session_state["chat_messages"][-1]["content"] = response
        st.rerun()
