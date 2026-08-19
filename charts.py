from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def _style_dark_figure(fig, title: str = "", height: int = 420):
    layout_update = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=35, r=35, t=70, b=35),
        legend=dict(
            font=dict(family="'Plus Jakarta Sans', sans-serif", size=12, color="#cbd5e1"),
            bgcolor="rgba(15, 23, 42, 0.4)",
            bordercolor="rgba(255, 255, 255, 0.05)",
            borderwidth=1
        ),
    )
    if title:
        layout_update["title"] = dict(
            text=title,
            font=dict(family="'Plus Jakarta Sans', sans-serif", size=17, color="#ffffff", weight="bold")
        )
    fig.update_layout(**layout_update)
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.05)",
        tickfont=dict(family="'Plus Jakarta Sans', sans-serif", color="#cbd5e1", size=11),
        title_font=dict(family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9", size=13),
        zeroline=False
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.05)",
        tickfont=dict(family="'Plus Jakarta Sans', sans-serif", color="#cbd5e1", size=11),
        title_font=dict(family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9", size=13),
        zeroline=False
    )
    return fig


def aging_bucket_distribution(summary_df: pd.DataFrame):
    if summary_df is None or summary_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Total Claim Count
    fig.add_trace(
        go.Bar(
            x=summary_df["aging_bucket"],
            y=summary_df["claim_count"],
            name="Total Claim Count",
            text=summary_df["claim_count"],
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            marker=dict(
                color="#2563eb",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Total Claims: %{y}<extra></extra>"
        )
    )

    # Total Claim Done
    fig.add_trace(
        go.Bar(
            x=summary_df["aging_bucket"],
            y=summary_df["done_count"],
            name="Total Claims Done",
            text=summary_df["done_count"],
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            marker=dict(
                color="#60a5fa",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Claims Done: %{y}<extra></extra>"
        )
    )

    _style_dark_figure(fig, title="Total Claim Count & Claims Done by Aging Bucket", height=450)
    fig.update_layout(
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    max_count = max(summary_df["claim_count"].max(), summary_df["done_count"].max()) if not summary_df.empty else 100
    fig.update_yaxes(title_text="Claim Count", range=[0, max_count * 1.15])
    fig.update_xaxes(title_text="Aging Bucket")

    return fig


def outstanding_balance_by_bucket(summary_df: pd.DataFrame):
    if summary_df is None or summary_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Total Balance
    fig.add_trace(
        go.Bar(
            x=summary_df["aging_bucket"],
            y=summary_df["total_claimed"],
            name="Total Balance",
            text=summary_df["total_claimed"].map(lambda x: f"${x/1e3:,.1f}K" if x >= 1000 else f"${x:,.0f}"),
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            marker=dict(
                color="#1d4ed8",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Total Balance: $%{y:,.2f}<extra></extra>"
        )
    )

    # Outstanding Balance
    fig.add_trace(
        go.Bar(
            x=summary_df["aging_bucket"],
            y=summary_df["outstanding_balance"],
            name="Outstanding Balance",
            text=summary_df["outstanding_balance"].map(lambda x: f"${x/1e3:,.1f}K" if x >= 1000 else f"${x:,.0f}"),
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            marker=dict(
                color="#06b6d4",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Outstanding Balance: $%{y:,.2f}<extra></extra>"
        )
    )

    _style_dark_figure(fig, title="Total Balance ($) & Outstanding Balance ($) by Aging Bucket", height=450)
    fig.update_layout(
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    max_bal = max(summary_df["total_claimed"].max(), summary_df["outstanding_balance"].max()) if not summary_df.empty else 100000
    fig.update_yaxes(title_text="Balance ($)", tickprefix="$", tickformat=",.0f", range=[0, max_bal * 1.15])
    fig.update_xaxes(title_text="Aging Bucket")

    return fig


def claims_worked_by_employee(productivity_df: pd.DataFrame):
    if productivity_df is None or productivity_df.empty:
        return go.Figure()
    fig = px.bar(
        productivity_df,
        x="total_touches",
        y="worked_by",
        orientation="h",
        color="worked_by",
        color_discrete_sequence=["#06b6d4", "#0284c7", "#3b82f6", "#6366f1", "#1d4ed8", "#1e40af"],
        labels={"total_touches": "Total Touches", "worked_by": "Employee"},
        text="total_touches",
    )
    fig.update_traces(
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1,
    )
    max_touches = productivity_df["total_touches"].max() if not productivity_df.empty else 100
    fig.update_xaxes(range=[0, max_touches * 1.15])
    return _style_dark_figure(fig, "Claims Worked by Employee")


def collection_amount_by_bucket(collection_df: pd.DataFrame):
    if collection_df is None or collection_df.empty:
        return go.Figure()
    fig = px.bar(
        collection_df,
        x="aging_bucket",
        y="recovered_amount",
        color="aging_bucket",
        color_discrete_sequence=["#06b6d4", "#0284c7", "#3b82f6", "#6366f1", "#1d4ed8", "#1e40af"],
        labels={"recovered_amount": "Recovered Amount ($)", "aging_bucket": "Aging Bucket"},
        text="recovered_amount",
    )
    fig.update_traces(
        texttemplate="<b>$%{text:,.0f}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1,
    )
    max_rec = collection_df["recovered_amount"].max() if not collection_df.empty else 100000
    fig.update_yaxes(range=[0, max_rec * 1.15])
    return _style_dark_figure(fig, "Collection Amount by Aging Bucket")


def collection_amount_by_employee(employee_collection_df: pd.DataFrame):
    if employee_collection_df is None or employee_collection_df.empty:
        return go.Figure()
    fig = px.bar(
        employee_collection_df,
        x="worked_by",
        y="recovered_amount",
        color="recovered_amount",
        color_continuous_scale="Blues",
        labels={"recovered_amount": "Recovered Amount ($)", "worked_by": "Employee"},
        text="recovered_amount",
    )
    fig.update_traces(
        texttemplate="<b>$%{text:,.0f}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1,
    )
    fig.update_layout(coloraxis_showscale=False)
    max_rec = employee_collection_df["recovered_amount"].max() if not employee_collection_df.empty else 100000
    fig.update_yaxes(range=[0, max_rec * 1.15])
    return _style_dark_figure(fig, "Collection Amount by Employee")


def worked_vs_recovered(productivity_df: pd.DataFrame, employee_collection_df: pd.DataFrame):
    if productivity_df is None or productivity_df.empty or employee_collection_df is None or employee_collection_df.empty:
        return go.Figure()
    merged = productivity_df.merge(employee_collection_df, on="worked_by", how="inner")
    if merged.empty:
        return go.Figure()
    fig = px.scatter(
        merged,
        x="total_touches",
        y="recovered_amount",
        size="unique_claims_touched",
        color="worked_by",
        color_discrete_sequence=["#60a5fa", "#3b82f6", "#2563eb", "#06b6d4", "#0284c7", "#6366f1"],
        labels={
            "total_touches": "Total Touches",
            "recovered_amount": "Recovered Amount ($)",
            "worked_by": "Employee",
            "unique_claims_touched": "Claims Touched"
        },
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color="rgba(255, 255, 255, 0.3)")),
        selector=dict(mode="markers"),
    )
    return _style_dark_figure(fig, "Worked Touches vs Recovered Amount")


def claims_trend_over_time(trend_df: pd.DataFrame):
    if trend_df is None or trend_df.empty:
        return go.Figure()
    fig = px.line(
        trend_df,
        x="snapshot_date",
        y=["total_claims", "open_claims"],
        markers=True,
        color_discrete_sequence=["#0284c7", "#93c5fd"],
        labels={"value": "Count", "snapshot_date": "Snapshot Date", "variable": "Claim Type"},
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color="#0f172a")))
    return _style_dark_figure(fig, "Claims Trend Over Time")


def outstanding_balance_trend(trend_df: pd.DataFrame):
    if trend_df is None or trend_df.empty:
        return go.Figure()
    fig = px.line(
        trend_df,
        x="snapshot_date",
        y="outstanding_balance",
        markers=True,
        color_discrete_sequence=["#3b82f6"],
        labels={"outstanding_balance": "Outstanding Balance ($)", "snapshot_date": "Snapshot Date"},
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color="#0f172a")))
    return _style_dark_figure(fig, "Outstanding Balance ($) Trend")


def recovery_trend(trend_df: pd.DataFrame):
    if trend_df is None or trend_df.empty:
        return go.Figure()
    fig = px.line(
        trend_df,
        x="snapshot_date",
        y="dollars_recovered",
        markers=True,
        color_discrete_sequence=["#00d2ff"],
        labels={"dollars_recovered": "Dollars Recovered ($)", "snapshot_date": "Snapshot Date"},
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color="#0f172a")))
    return _style_dark_figure(fig, "Balance Reductions ($) Trend")


def aging_bucket_trend(aging_df: pd.DataFrame):
    if aging_df is None or aging_df.empty:
        return go.Figure()
    fig = px.bar(
        aging_df,
        x="snapshot_date",
        y="claim_count",
        color="aging_bucket",
        color_discrete_sequence=["#1e3a8a", "#1d4ed8", "#3b82f6", "#60a5fa"],
        barmode="stack",
        labels={"claim_count": "Claim Count", "snapshot_date": "Snapshot Date", "aging_bucket": "Aging Bucket"},
    )
    return _style_dark_figure(fig, "Aging Bucket Trend")


def claims_worked_trend(trend_df: pd.DataFrame):
    if trend_df is None or trend_df.empty:
        return go.Figure()
    fig = px.line(
        trend_df,
        x="snapshot_date",
        y="claims_worked",
        markers=True,
        color_discrete_sequence=["#38bdf8"],
        labels={"claims_worked": "Claims Worked", "snapshot_date": "Snapshot Date"},
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color="#0f172a")))
    return _style_dark_figure(fig, "Claims Worked Trend")


def claims_done_distribution(done_df: pd.DataFrame):
    if done_df is None or done_df.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    max_count = float(done_df["done_count"].max()) if not done_df["done_count"].empty else 100
    max_cost = float(done_df["recovered_amount"].max()) if not done_df["recovered_amount"].empty else 100000

    # Left Bar: Done Claims Count (Primary Y-axis)
    fig.add_trace(
        go.Bar(
            x=done_df["aging_bucket"],
            y=done_df["done_count"],
            name="Claims Done (Count)",
            text=done_df["done_count"],
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            cliponaxis=False,
            offsetgroup=1,
            marker=dict(
                color="#2563eb",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Claims Done: %{y}<extra></extra>"
        ),
        secondary_y=False,
    )

    # Right Bar: Recovered Amount (Secondary Y-axis)
    fig.add_trace(
        go.Bar(
            x=done_df["aging_bucket"],
            y=done_df["recovered_amount"],
            name="Amount Recovered ($)",
            text=done_df["recovered_amount"].map(lambda x: f"${x/1e3:,.1f}K" if x >= 1000 else f"${x:,.0f}"),
            textposition="outside",
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12, family="'Plus Jakarta Sans', sans-serif", color="#f1f5f9"),
            cliponaxis=False,
            offsetgroup=2,
            marker=dict(
                color="#00d2ff",
                line=dict(color="rgba(255, 255, 255, 0.1)", width=0.5)
            ),
            hovertemplate="Aging Bucket: %{x}<br>Amount Recovered: $%{y:,.2f}<extra></extra>"
        ),
        secondary_y=True,
    )

    _style_dark_figure(fig, title="Total Claims Done & Value by Aging Bucket", height=450)
    fig.update_layout(
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    fig.update_yaxes(title_text="Claims Done (Count)", range=[0, max_count * 1.18], secondary_y=False)
    fig.update_yaxes(title_text="Amount Recovered ($)", range=[0, max_cost * 1.18], secondary_y=True, tickprefix="$", tickformat=",.0f")
    fig.update_xaxes(title_text="Aging Bucket")

    return fig


def snapshot_progression_trend(prog_df: pd.DataFrame):
    if prog_df is None or prog_df.empty:
        return go.Figure()
    
    # Ensure sorted by date
    df = prog_df.sort_values("snapshot_date").copy()
    
    # Map snapshot dates to Week labels
    target_dates = [
        pd.to_datetime("2026-05-04").date(),
        pd.to_datetime("2026-05-11").date(),
        pd.to_datetime("2026-05-18").date(),
        pd.to_datetime("2026-05-26").date(),
    ]
    
    df["date_only"] = df["snapshot_date"].dt.date
    df = df[df["date_only"].isin(target_dates)].copy()
    
    date_to_week = {
        target_dates[0]: "Week 1",
        target_dates[1]: "Week 2",
        target_dates[2]: "Week 3",
        target_dates[3]: "Week 4"
    }
    df["week_label"] = df["date_only"].map(date_to_week)
    df = df.dropna(subset=["week_label"]).sort_values("snapshot_date")
    
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    
    outstanding_ar = df["outstanding_balance"].tolist()
    outstanding_ar_text = [f"<b>${v/1e6:.3f}M</b>" for v in outstanding_ar]
    
    fig.add_trace(
        go.Scatter(
            x=df["week_label"],
            y=outstanding_ar,
            name="Outstanding AR ($)",
            mode="lines+markers+text",
            line=dict(color="#3b82f6", width=4),
            marker=dict(size=10, symbol="circle", line=dict(color="#030712", width=2)),
            text=outstanding_ar_text,
            textposition="top center",
            textfont=dict(family="'Plus Jakarta Sans', sans-serif", size=12, color="#3b82f6"),
            hovertemplate="Week: %{x}<br>Outstanding AR: $%{y:,.2f}<extra></extra>"
        )
    )
    
    _style_dark_figure(fig, title="Week-over-Week Outstanding AR Progression", height=450)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=60, r=60, t=50, b=50),
    )
    
    # Configure axes
    min_ar = min(outstanding_ar)
    max_ar = max(outstanding_ar)
    fig.update_yaxes(
        title_text="Outstanding AR ($)", 
        range=[min_ar - 20000, max_ar + 20000],
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.05)",
        tickprefix="$", 
        tickformat=",.0f"
    )
    
    fig.update_xaxes(
        title_text="",
        showgrid=False
    )
    return fig


def follow_up_frequency_chart(freq_df: pd.DataFrame):
    if freq_df is None or freq_df.empty:
        return go.Figure()
    
    fig = px.bar(
        freq_df,
        x="touch_count",
        y="claim_count",
        labels={"touch_count": "Touch Frequency in Month", "claim_count": "Claims Count"},
        color="touch_count",
        color_discrete_sequence=["#06b6d4", "#0284c7", "#3b82f6", "#6366f1", "#1d4ed8", "#1e40af"],
        text="claim_count"
    )
    
    fig.update_traces(
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1,
        hovertemplate="Touched %{x} times: %{y} claims<extra></extra>"
    )
    
    max_val = freq_df["claim_count"].max() if not freq_df.empty else 100
    fig.update_yaxes(range=[0, max_val * 1.15])
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category")
    
    return _style_dark_figure(fig, "Claim Follow-up Touch Frequency Distribution")


def employee_follow_up_chart(follow_df: pd.DataFrame):
    if follow_df is None or follow_df.empty:
        return go.Figure()
    
    fig = px.bar(
        follow_df,
        x="follow_up_touches",
        y="worked_by",
        orientation="h",
        color="worked_by",
        color_discrete_sequence=["#06b6d4", "#0284c7", "#3b82f6", "#6366f1", "#1d4ed8", "#1e40af"],
        labels={"follow_up_touches": "Follow-up Touches", "worked_by": "Employee"},
        text="follow_up_touches"
    )
    
    fig.update_traces(
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1
    )
    
    max_val = follow_df["follow_up_touches"].max() if not follow_df.empty else 100
    fig.update_xaxes(range=[0, max_val * 1.15])
    fig.update_layout(showlegend=False)
    
    return _style_dark_figure(fig, "Employee Follow-up Touches on Multi-touch Claims")


def executive_productivity_trend_chart(prog_df: pd.DataFrame):
    if prog_df is None or prog_df.empty:
        return go.Figure()
    
    # Ensure sorted by date
    df = prog_df.sort_values("snapshot_date").copy()
    
    # Map snapshot dates to Week labels
    target_dates = [
        pd.to_datetime("2026-05-04").date(),
        pd.to_datetime("2026-05-11").date(),
        pd.to_datetime("2026-05-18").date(),
        pd.to_datetime("2026-05-26").date(),
    ]
    
    df["date_only"] = df["snapshot_date"].dt.date
    df = df[df["date_only"].isin(target_dates)].copy()
    
    date_to_week = {
        target_dates[0]: "Week 1",
        target_dates[1]: "Week 2",
        target_dates[2]: "Week 3",
        target_dates[3]: "Week 4"
    }
    df["week_label"] = df["date_only"].map(date_to_week)
    df = df.dropna(subset=["week_label"]).sort_values("snapshot_date")
    
    if df.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Line 1: Claim Count (Left Axis - Royal Blue)
    claim_counts = df["total_claims"].tolist()
    claim_count_text = [f"<b>{int(c):,}</b>" for c in claim_counts]
    
    fig.add_trace(
        go.Scatter(
            x=df["week_label"],
            y=claim_counts,
            name="Claim Count",
            mode="lines+markers+text",
            line=dict(color="#2563eb", width=4),
            marker=dict(size=10, symbol="circle", line=dict(color="#030712", width=2)),
            text=claim_count_text,
            textposition="top center",
            textfont=dict(family="'Plus Jakarta Sans', sans-serif", size=12, color="#2563eb"),
            hovertemplate="Week: %{x}<br>Claim Count: %{y:,}<extra></extra>"
        ),
        secondary_y=False
    )
    
    # Line 2: Outstanding AR (Right Axis - Sky Blue)
    outstanding_ar = df["outstanding_balance"].tolist()
    outstanding_ar_text = [f"<b>${v/1e6:.3f}M</b>" for v in outstanding_ar]
    
    fig.add_trace(
        go.Scatter(
            x=df["week_label"],
            y=outstanding_ar,
            name="Outstanding AR ($)",
            mode="lines+markers+text",
            line=dict(color="#00d2ff", width=4),
            marker=dict(size=10, symbol="circle", line=dict(color="#030712", width=2)),
            text=outstanding_ar_text,
            textposition="bottom center",
            textfont=dict(family="'Plus Jakarta Sans', sans-serif", size=12, color="#00d2ff"),
            hovertemplate="Week: %{x}<br>Outstanding AR: $%{y:,.2f}<extra></extra>"
        ),
        secondary_y=True
    )
    
    # Apply styling
    _style_dark_figure(fig, title="", height=480)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    
    # Configure axes
    min_count = min(claim_counts)
    max_count = max(claim_counts)
    fig.update_yaxes(
        title_text="Claim Count", 
        secondary_y=False,
        range=[min_count - 50, max_count + 50],
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.05)"
    )
    
    min_ar = min(outstanding_ar)
    max_ar = max(outstanding_ar)
    fig.update_yaxes(
        title_text="Outstanding AR ($)", 
        secondary_y=True,
        range=[min_ar - 20000, max_ar + 20000],
        showgrid=False
    )
    
    fig.update_xaxes(
        title_text="",
        showgrid=False
    )
    
    return fig


def bucket_follow_up_chart(bucket_df: pd.DataFrame):
    if bucket_df is None or bucket_df.empty:
        return go.Figure()
    
    fig = px.bar(
        bucket_df,
        x="aging_bucket",
        y="follow_up_count",
        labels={"aging_bucket": "Aging Bucket", "follow_up_count": "Follow-up Claims Count"},
        color="aging_bucket",
        color_discrete_sequence=["#06b6d4", "#0284c7", "#3b82f6", "#6366f1"],
        text="follow_up_count"
    )
    
    fig.update_traces(
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont=dict(size=12, color="#f1f5f9", family="'Plus Jakarta Sans', sans-serif"),
        cliponaxis=False,
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1,
        hovertemplate="Aging Bucket: %{x}<br>Follow-up Claims: %{y}<extra></extra>"
    )
    
    max_val = bucket_df["follow_up_count"].max() if not bucket_df.empty else 100
    fig.update_yaxes(range=[0, max_val * 1.15])
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category")
    
    return _style_dark_figure(fig, "Claims Followed Up (>1 Touch) by Aging Bucket")

