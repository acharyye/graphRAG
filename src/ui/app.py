"""Marketing GraphRAG - Modern UI."""

import io
import os
import sys
from datetime import datetime, timedelta, date
from uuid import uuid4

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GraphRAG",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>G</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design System CSS
# ---------------------------------------------------------------------------
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ---- Base ---- */
.stApp {
    background-color: #f9fafb;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.stApp, .stApp * { color: #111827; }

#MainMenu, footer { visibility: hidden; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] * { color: #111827 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stDateInput label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280 !important;
}

/* ---- Cards ---- */
.metric-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    transition: box-shadow 0.15s ease;
}
.metric-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.metric-card .label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    margin-bottom: 0.35rem;
}
.metric-card .value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #111827;
    line-height: 1.2;
}
.metric-card .trend-up {
    font-size: 0.8rem;
    font-weight: 500;
    color: #059669;
    margin-top: 0.25rem;
}
.metric-card .trend-down {
    font-size: 0.8rem;
    font-weight: 500;
    color: #dc2626;
    margin-top: 0.25rem;
}

/* ---- Insight banner ---- */
.insight-banner {
    background: linear-gradient(135deg, #eef2ff 0%, #faf5ff 100%);
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}
.insight-banner .title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6366f1;
    margin-bottom: 0.4rem;
}
.insight-banner p {
    color: #374151;
    font-size: 0.95rem;
    line-height: 1.6;
    margin: 0;
}

/* ---- Section headers ---- */
.section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #111827;
    margin: 1.25rem 0 0.75rem 0;
}

/* ---- Page header ---- */
.page-header {
    font-size: 1.5rem;
    font-weight: 700;
    color: #111827;
    margin-bottom: 0.15rem;
}
.page-desc {
    color: #6b7280;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* ---- Brand ---- */
.brand-mark {
    font-weight: 700;
    font-size: 1.125rem;
    margin-bottom: 0.15rem;
}
.brand-mark span {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.brand-sub {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-bottom: 1rem;
}

/* ---- Confidence badges ---- */
.conf-badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}
.conf-high { background: #ecfdf5; color: #059669; }
.conf-medium { background: #fffbeb; color: #d97706; }
.conf-low { background: #fef2f2; color: #dc2626; }

/* ---- Source tags ---- */
.source-tag {
    display: inline-block;
    background: #f3f4f6;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.78rem;
    color: #6b7280;
    margin: 0.15rem;
}

/* ---- Status badges ---- */
.status-active {
    display: inline-block;
    background: #ecfdf5;
    color: #059669;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}
.status-paused {
    display: inline-block;
    background: #fffbeb;
    color: #d97706;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}
.status-error {
    display: inline-block;
    background: #fef2f2;
    color: #dc2626;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}

/* ---- Suggestion pills ---- */
.suggestion-pill {
    display: inline-block;
    padding: 0.45rem 1rem;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 9999px;
    font-size: 0.85rem;
    color: #374151;
    margin: 0.25rem;
    cursor: pointer;
    transition: all 0.15s ease;
}
.suggestion-pill:hover {
    border-color: #6366f1;
    color: #6366f1;
    background: #eef2ff;
}

/* ---- Login ---- */
.login-card {
    max-width: 420px;
    margin: 4rem auto;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}
.login-brand {
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.login-brand span {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.login-sub {
    text-align: center;
    color: #6b7280;
    font-size: 0.9rem;
    margin-bottom: 2rem;
}

/* ---- Platform card ---- */
.platform-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
}
.platform-card.connected {
    border-color: #a7f3d0;
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
}
.platform-name {
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 0.5rem;
}

/* ---- Empty state ---- */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #9ca3af;
}
.empty-state h3 {
    color: #374151;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* ---- Streamlit widget overrides ---- */

/* Buttons */
.stButton button {
    background: #6366f1 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: background 0.15s ease !important;
    font-family: 'Inter', sans-serif !important;
}
.stButton button:hover {
    background: #4f46e5 !important;
}

/* Text inputs */
.stTextInput input, .stNumberInput input {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.08) !important;
}

/* Labels */
.stTextInput label, .stSelectbox label, .stDateInput label,
.stNumberInput label, .stMultiSelect label, .stFileUploader label {
    color: #374151 !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}

/* Selectbox */
.stSelectbox > div > div {
    border-radius: 8px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #f3f4f6;
    border-radius: 10px;
    padding: 0.25rem;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #6b7280 !important;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    font-size: 0.85rem;
    font-family: 'Inter', sans-serif;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #111827 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}

/* Metrics */
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #111827 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #6b7280 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-family: 'Inter', sans-serif !important;
}

/* Dataframes */
.stDataFrame { border-radius: 12px !important; overflow: hidden; }

/* Chat */
.stChatMessage {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stChatMessageContent"] { color: #111827 !important; }
.stChatInput, .stChatInput textarea {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
}
.stChatInput textarea::placeholder { color: #9ca3af !important; }
.stMarkdown, .stMarkdown p, .stMarkdown span { color: #111827 !important; }

/* Expander */
.streamlit-expanderHeader {
    color: #111827 !important;
    background: #f9fafb !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}
.streamlit-expanderContent { color: #111827 !important; }

/* Alerts */
.stAlert { border-radius: 10px !important; }

/* Dividers */
hr { border-color: #f3f4f6 !important; }

/* Radio navigation in sidebar */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0.125rem;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    font-size: 0.9rem !important;
    transition: background 0.1s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #f3f4f6;
}

/* Form submit buttons */
.stFormSubmitButton button {
    background: #6366f1 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stFormSubmitButton button:hover {
    background: #4f46e5 !important;
}

/* Download buttons */
.stDownloadButton button {
    background: #ffffff !important;
    color: #374151 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
}
.stDownloadButton button:hover {
    background: #f9fafb !important;
    border-color: #6366f1 !important;
    color: #6366f1 !important;
}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants & Session State
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

for key, default in {
    "token": None,
    "user": None,
    "selected_client": None,
    "chat_history": [],
    "session_id": str(uuid4()),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_request(method: str, endpoint: str, **kwargs):
    """Make an authenticated API request."""
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    url = f"{API_BASE_URL}{endpoint}"
    try:
        return requests.request(method, url, headers=headers, timeout=60, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the server. Please make sure the API is running.")
        return None
    except requests.exceptions.Timeout:
        st.error("The request timed out. Please try again.")
        return None


def _greeting():
    """Return a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"


def _fmt_currency(v, compact=False):
    if v is None:
        return "$0"
    if compact and abs(v) >= 1000:
        return f"${v/1000:,.1f}k"
    return f"${v:,.0f}"


def _fmt_number(v, compact=False):
    if v is None:
        return "0"
    if compact and abs(v) >= 1_000_000:
        return f"{v/1_000_000:,.1f}M"
    if compact and abs(v) >= 1000:
        return f"{v/1000:,.1f}k"
    return f"{v:,.0f}"


# ---------------------------------------------------------------------------
# Login Page
# ---------------------------------------------------------------------------

def login_page():
    """Clean, centered login page."""
    st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
        <div class="login-card">
            <div class="login-brand"><span>GraphRAG</span></div>
            <div class="login-sub">Marketing intelligence, powered by AI</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

            if submitted:
                response = api_request(
                    "POST", "/auth/login",
                    json={"email": email, "password": password},
                )
                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.rerun()
                else:
                    st.error("Invalid email or password. Please try again.")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def sidebar():
    """Sidebar: branding, client picker, navigation, date range, sign-out."""
    with st.sidebar:
        # Brand
        st.markdown('<div class="brand-mark"><span>GraphRAG</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Marketing Intelligence</div>', unsafe_allow_html=True)

        user = st.session_state.user
        st.caption(f"Signed in as **{user['name']}**")

        st.divider()

        # Navigation
        nav_items = ["Home", "Ask", "Reports", "Data Sources"]
        if user.get("role") == "admin":
            nav_items.append("Settings")

        page = st.radio(
            "Navigation",
            nav_items,
            label_visibility="collapsed",
        )

        st.divider()

        # Client picker
        st.markdown(
            "<div style='font-size:0.75rem;font-weight:600;text-transform:uppercase;"
            "letter-spacing:0.05em;color:#6b7280;margin-bottom:0.25rem'>Account</div>",
            unsafe_allow_html=True,
        )
        response = api_request("GET", "/ingest/clients")

        if response and response.status_code == 200:
            clients = response.json().get("clients", [])
            if clients:
                # Deduplicate by name
                seen = set()
                unique = []
                for c in clients:
                    if c["name"] not in seen:
                        seen.add(c["name"])
                        unique.append(c)

                names = {c["id"]: c["name"] for c in unique}
                selected_id = st.selectbox(
                    "Account",
                    options=list(names.keys()),
                    format_func=lambda x: names[x],
                    label_visibility="collapsed",
                )
                st.session_state.selected_client = next(
                    (c for c in unique if c["id"] == selected_id), None
                )
            else:
                st.info("No accounts yet")
        else:
            st.warning("Could not load accounts")

        st.divider()

        # Date range
        st.markdown(
            "<div style='font-size:0.75rem;font-weight:600;text-transform:uppercase;"
            "letter-spacing:0.05em;color:#6b7280;margin-bottom:0.25rem'>Date Range</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input(
                "From", value=datetime.now() - timedelta(days=30), label_visibility="collapsed"
            )
        with c2:
            end_date = st.date_input(
                "To", value=datetime.now(), label_visibility="collapsed"
            )
        st.session_state.date_range = (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        # Spacer + sign-out
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            for k in ["token", "user", "chat_history", "selected_client"]:
                st.session_state[k] = None
            st.session_state.session_id = str(uuid4())
            st.rerun()

        return page


# ---------------------------------------------------------------------------
# HOME (Dashboard)
# ---------------------------------------------------------------------------

def home_page():
    """Insight-first dashboard for the selected client."""
    user = st.session_state.user
    client = st.session_state.selected_client

    # Welcome
    st.markdown(
        f'<div class="page-header">{_greeting()}, {user["name"].split()[0]}</div>',
        unsafe_allow_html=True,
    )

    if not client:
        st.markdown('<div class="page-desc">Select an account from the sidebar to get started.</div>', unsafe_allow_html=True)
        return

    st.markdown(
        f'<div class="page-desc">Here\'s how <strong>{client["name"]}</strong> is performing '
        f'({st.session_state.date_range[0]} to {st.session_state.date_range[1]})</div>',
        unsafe_allow_html=True,
    )

    client_id = client["id"]

    # Fetch data
    with st.spinner("Loading performance data..."):
        response = api_request(
            "GET",
            f"/dashboard/{client_id}"
            f"?start_date={st.session_state.date_range[0]}"
            f"&end_date={st.session_state.date_range[1]}",
        )

    if response and response.status_code == 200:
        data = response.json()
        summary = data.get("summary", {})
        daily_metrics = data.get("daily_metrics", [])
        channel_breakdown = data.get("channel_breakdown", [])
        campaigns = data.get("campaigns", [])
    else:
        summary = _fetch_metrics_summary(client_id)
        daily_metrics = _fetch_daily_metrics(client_id)
        channel_breakdown = _fetch_channel_breakdown(client_id)
        campaigns = _fetch_campaigns(client_id)

    # ---- Insight banner ----
    spend = summary.get("total_spend", 0) or 0
    conversions = summary.get("total_conversions", 0) or 0
    roas = summary.get("roas", 0) or 0

    if spend > 0 and conversions > 0:
        cpa = spend / conversions if conversions else 0
        insight_lines = []
        if roas >= 3:
            insight_lines.append(f"Strong return on ad spend at <strong>{roas:.1f}x</strong>.")
        elif roas >= 1:
            insight_lines.append(f"Your return on ad spend is <strong>{roas:.1f}x</strong> &mdash; profitable but with room to grow.")
        else:
            insight_lines.append(f"Return on ad spend is below break-even at <strong>{roas:.1f}x</strong>. Consider reviewing underperforming campaigns.")
        insight_lines.append(
            f"You generated <strong>{_fmt_number(conversions)}</strong> conversions "
            f"at <strong>{_fmt_currency(cpa)}</strong> per conversion."
        )
        st.markdown(
            '<div class="insight-banner">'
            '<div class="title">Key Insight</div>'
            f'<p>{"<br>".join(insight_lines)}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ---- KPI cards ----
    cols = st.columns(5)
    kpis = [
        ("Ad Spend", _fmt_currency(spend, compact=True)),
        ("Impressions", _fmt_number(summary.get("total_impressions", 0), compact=True)),
        ("Clicks", _fmt_number(summary.get("total_clicks", 0), compact=True)),
        ("Conversions", _fmt_number(conversions, compact=True)),
        ("ROAS", f"{roas:.1f}x" if roas else "N/A"),
    ]
    for col, (label, value) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="label">{label}</div>'
                f'<div class="value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ---- Charts row ----
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown('<div class="section-title">Performance Over Time</div>', unsafe_allow_html=True)
        if daily_metrics:
            df = pd.DataFrame(daily_metrics)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                fig = go.Figure()
                spend_col = "spend" if "spend" in df.columns else "total_spend"
                conv_col = "conversions" if "conversions" in df.columns else "total_conversions"
                if spend_col in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["date"], y=df[spend_col],
                        name="Spend", line=dict(color="#6366f1", width=2),
                        fill="tozeroy", fillcolor="rgba(99,102,241,0.06)",
                    ))
                if conv_col in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["date"], y=df[conv_col],
                        name="Conversions", line=dict(color="#10b981", width=2),
                        yaxis="y2",
                    ))
                fig.update_layout(
                    height=320,
                    margin=dict(l=0, r=0, t=10, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    yaxis=dict(title=None, showgrid=True, gridcolor="#f3f4f6"),
                    yaxis2=dict(title=None, overlaying="y", side="right", showgrid=False),
                    xaxis=dict(showgrid=False),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", size=12, color="#6b7280"),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily data for the selected period.")

    with c2:
        st.markdown('<div class="section-title">Spend by Channel</div>', unsafe_allow_html=True)
        if channel_breakdown:
            ch_df = pd.DataFrame(channel_breakdown)
            spend_key = "spend" if "spend" in ch_df.columns else "total_spend"
            fig = px.pie(
                ch_df, values=spend_key, names="channel",
                color_discrete_sequence=["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#10b981", "#f59e0b"],
                hole=0.55,
            )
            fig.update_layout(
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.05),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12, color="#6b7280"),
            )
            fig.update_traces(textinfo="percent", textfont_size=12)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No channel data available.")

    # ---- Campaign table ----
    st.markdown('<div class="section-title">Top Campaigns</div>', unsafe_allow_html=True)
    if campaigns:
        camp_df = pd.DataFrame(campaigns)
        display_cols = ["name", "channel", "status", "spend", "clicks", "conversions", "ctr", "roas"]
        available = [c for c in display_cols if c in camp_df.columns]
        if available:
            st.dataframe(
                camp_df[available],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "name": st.column_config.TextColumn("Campaign"),
                    "channel": st.column_config.TextColumn("Channel"),
                    "status": st.column_config.TextColumn("Status"),
                    "spend": st.column_config.NumberColumn("Spend", format="$%.0f"),
                    "clicks": st.column_config.NumberColumn("Clicks"),
                    "conversions": st.column_config.NumberColumn("Conversions"),
                    "ctr": st.column_config.NumberColumn("CTR", format="%.2f%%"),
                    "roas": st.column_config.NumberColumn("ROAS", format="%.1fx"),
                },
            )
    else:
        st.markdown(
            '<div class="empty-state"><h3>No campaigns yet</h3>'
            'Import data or connect an ad platform to see campaign performance here.</div>',
            unsafe_allow_html=True,
        )


# ---- Dashboard fallback queries (use correct Neo4j relationships) ----

def _fetch_metrics_summary(client_id: str) -> dict:
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()
        s, e = st.session_state.date_range
        result = neo4j.execute_query("""
            MATCH (m:Metric)
            WHERE m.client_id = $client_id
              AND m.date >= date($start) AND m.date <= date($end)
            RETURN
                sum(m.spend) as total_spend,
                sum(m.impressions) as total_impressions,
                sum(m.clicks) as total_clicks,
                sum(m.conversions) as total_conversions,
                CASE WHEN sum(m.impressions) > 0
                     THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as avg_ctr,
                CASE WHEN sum(m.spend) > 0
                     THEN sum(m.revenue) / sum(m.spend) ELSE 0 END as roas
        """, {"client_id": client_id, "start": s, "end": e})
        return dict(result[0]) if result else {}
    except Exception:
        return {}


def _fetch_daily_metrics(client_id: str) -> list:
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()
        s, e = st.session_state.date_range
        result = neo4j.execute_query("""
            MATCH (m:Metric)
            WHERE m.client_id = $client_id
              AND m.date >= date($start) AND m.date <= date($end)
            RETURN
                toString(m.date) as date,
                sum(m.spend) as spend,
                sum(m.conversions) as conversions
            ORDER BY date
        """, {"client_id": client_id, "start": s, "end": e})
        return [dict(r) for r in result] if result else []
    except Exception:
        return []


def _fetch_channel_breakdown(client_id: str) -> list:
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()
        s, e = st.session_state.date_range
        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:RUNS_ON]->(ch:Channel)
            OPTIONAL MATCH (m:Metric)
            WHERE m.entity_id = camp.id
              AND m.date >= date($start) AND m.date <= date($end)
            RETURN
                ch.name as channel,
                sum(m.spend) as spend,
                sum(m.conversions) as conversions
        """, {"client_id": client_id, "start": s, "end": e})
        return [dict(r) for r in result] if result else []
    except Exception:
        return []


def _fetch_campaigns(client_id: str) -> list:
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()
        s, e = st.session_state.date_range
        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
            OPTIONAL MATCH (camp)-[:RUNS_ON]->(ch:Channel)
            OPTIONAL MATCH (m:Metric)
            WHERE m.entity_id = camp.id
              AND m.date >= date($start) AND m.date <= date($end)
            RETURN
                camp.name as name,
                ch.name as channel,
                camp.status as status,
                sum(m.spend) as spend,
                sum(m.clicks) as clicks,
                sum(m.conversions) as conversions,
                CASE WHEN sum(m.impressions) > 0
                     THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as ctr,
                CASE WHEN sum(m.spend) > 0
                     THEN sum(m.revenue) / sum(m.spend) ELSE 0 END as roas
            ORDER BY spend DESC
            LIMIT 20
        """, {"client_id": client_id, "start": s, "end": e})
        return [dict(r) for r in result] if result else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# ASK (Natural Language Query)
# ---------------------------------------------------------------------------

def ask_page():
    """Conversational query interface with marketing-friendly language."""
    st.markdown('<div class="page-header">Ask a question</div>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.markdown(
            '<div class="page-desc">Select an account from the sidebar, then ask anything about your marketing performance.</div>',
            unsafe_allow_html=True,
        )
        return

    client = st.session_state.selected_client
    st.markdown(
        f'<div class="page-desc">Ask anything about <strong>{client["name"]}</strong>\'s campaigns, spend, or performance.</div>',
        unsafe_allow_html=True,
    )

    # Suggestions (only when chat is empty)
    if not st.session_state.chat_history:
        suggestions = [
            "Which campaign had the best return last month?",
            "How is our spend split across channels?",
            "What trends do you see in our conversion rate?",
            "Which ads should we pause to save budget?",
        ]
        pills_html = "".join(
            f'<span class="suggestion-pill">{s}</span>' for s in suggestions
        )
        st.markdown(
            f'<div style="margin-bottom:1.5rem">'
            f'<div style="font-size:0.8rem;font-weight:500;color:#9ca3af;margin-bottom:0.5rem">Try asking</div>'
            f'{pills_html}</div>',
            unsafe_allow_html=True,
        )

    # Chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Confidence
            if msg.get("confidence"):
                conf = msg["confidence"]
                level = conf.get("level", "medium")
                overall = conf.get("overall", 0)
                label_map = {"high": "High confidence", "medium": "Moderate confidence", "low": "Low confidence"}
                st.markdown(
                    f'<span class="conf-badge conf-{level}">{label_map.get(level, level)} &middot; {overall:.0%}</span>',
                    unsafe_allow_html=True,
                )

            # Sources
            if msg.get("sources"):
                with st.expander("View sources"):
                    for src in msg["sources"]:
                        name = src.get("entity_name", src.get("entity_id", ""))
                        etype = src.get("entity_type", "")
                        dr = src.get("date_range", "")
                        st.markdown(f'<span class="source-tag">{etype}: {name} ({dr})</span>', unsafe_allow_html=True)

            # Recommendations
            if msg.get("recommendations"):
                with st.expander("Suggested next steps"):
                    for rec in msg["recommendations"]:
                        st.markdown(f"- {rec}")

    # Input
    query = st.chat_input("Ask about campaigns, performance, spend, trends...")

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.spinner("Analyzing your data..."):
            response = api_request(
                "POST", "/query",
                json={
                    "query": query,
                    "client_id": client["id"],
                    "session_id": st.session_state.session_id,
                    "date_range": st.session_state.date_range,
                },
            )
        if response and response.status_code == 200:
            data = response.json()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": data["answer"],
                "sources": data.get("sources", []),
                "confidence": data.get("confidence"),
                "recommendations": data.get("recommendations"),
            })
        else:
            err = "Something went wrong. Please try rephrasing your question."
            if response:
                err = response.json().get("detail", err)
            st.session_state.chat_history.append({"role": "assistant", "content": err})
        st.rerun()

    # Clear button
    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.session_state.session_id = str(uuid4())
            st.rerun()


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

def reports_page():
    """Report generation and scheduling."""
    st.markdown('<div class="page-header">Reports</div>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.markdown('<div class="page-desc">Select an account to generate or schedule reports.</div>', unsafe_allow_html=True)
        return

    client = st.session_state.selected_client
    client_id = client["id"]
    st.markdown(f'<div class="page-desc">Generate and schedule reports for <strong>{client["name"]}</strong>.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Generate", "Schedules"])

    # ---- Generate ----
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            report_type = st.selectbox("Report type", ["Monthly", "Weekly", "Daily", "Quarterly", "Custom"])
            format_option = st.selectbox("File format", ["PDF", "Excel", "CSV"])
        with c2:
            sections = st.multiselect(
                "Include sections",
                ["Summary", "Campaigns", "Ad Sets", "Trends", "Recommendations", "Channel Breakdown"],
                default=["Summary", "Campaigns", "Trends", "Recommendations"],
            )
            compare = st.checkbox("Compare with previous period", value=True)

        if st.button("Generate report", type="primary", use_container_width=True):
            section_map = {
                "Summary": "summary", "Campaigns": "campaigns", "Ad Sets": "ad_sets",
                "Trends": "trends", "Recommendations": "recommendations",
                "Channel Breakdown": "channel_breakdown",
            }
            with st.spinner("Generating report..."):
                resp = api_request("POST", "/reports", json={
                    "client_id": client_id,
                    "report_type": report_type.lower(),
                    "format": format_option.lower(),
                    "date_range": {"start": st.session_state.date_range[0], "end": st.session_state.date_range[1]},
                    "sections": [section_map[s] for s in sections],
                    "include_recommendations": "Recommendations" in sections,
                    "compare_to_previous": compare,
                })
            if resp and resp.status_code == 202:
                st.success(f"Report queued. ID: {resp.json()['report_id']}")
            else:
                st.error("Failed to generate report. Please try again.")

        # Recent reports
        st.markdown('<div class="section-title">Recent Reports</div>', unsafe_allow_html=True)
        resp = api_request("GET", f"/reports?client_id={client_id}")
        if resp and resp.status_code == 200:
            reports = resp.json().get("reports", [])
            if reports:
                for r in reports[:10]:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1:
                        st.markdown(f"**{r['report_type'].title()}** &mdash; {r['date_range']['start']} to {r['date_range']['end']}")
                    with c2:
                        st.markdown(f"`{r['format'].upper()}`")
                    with c3:
                        status_cls = {"completed": "status-active", "generating": "status-paused", "failed": "status-error"}.get(r["status"], "status-paused")
                        st.markdown(f'<span class="{status_cls}">{r["status"].title()}</span>', unsafe_allow_html=True)
                    with c4:
                        if r["status"] == "completed" and r.get("download_url"):
                            st.markdown(f"[Download]({API_BASE_URL}{r['download_url']})")
            else:
                st.info("No reports generated yet.")
        else:
            st.warning("Could not load reports.")

    # ---- Schedules ----
    with tab2:
        st.markdown("Set up reports to be automatically generated and delivered to your inbox.")

        with st.form("schedule_form"):
            c1, c2 = st.columns(2)
            with c1:
                freq = st.selectbox("Frequency", ["daily", "weekly", "monthly"], format_func=str.title)
                fmt = st.selectbox("Format", ["pdf", "excel"], format_func=str.upper, key="sched_fmt")
            with c2:
                email = st.text_input("Delivery email", placeholder="reports@company.com")
                time_val = st.time_input("Delivery time", value=datetime.strptime("09:00", "%H:%M").time())

            if st.form_submit_button("Create schedule", use_container_width=True):
                if email:
                    resp = api_request("POST", "/schedules/reports", json={
                        "client_id": client_id, "frequency": freq,
                        "report_type": "monthly", "format": fmt,
                        "email": email, "time_of_day": time_val.strftime("%H:%M"),
                    })
                    if resp and resp.status_code == 201:
                        st.success(f"Schedule created. {freq.title()} reports will be sent to {email}.")
                    else:
                        detail = resp.json().get("detail", "Unknown error") if resp else "Connection error"
                        st.error(f"Could not create schedule: {detail}")
                else:
                    st.warning("Please enter an email address.")

        st.markdown('<div class="section-title">Active Schedules</div>', unsafe_allow_html=True)
        sched_resp = api_request("GET", f"/schedules/reports?client_id={client_id}")
        if sched_resp and sched_resp.status_code == 200:
            schedules = sched_resp.json()
            if schedules:
                for s in schedules:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1:
                        st.markdown(f"**{s['frequency'].title()}** to {s['email']} at {s.get('time_of_day', '09:00')}")
                    with c2:
                        st.markdown(f"`{s.get('format', 'pdf').upper()}`")
                    with c3:
                        badge = "status-active" if s.get("enabled") else "status-paused"
                        label = "Active" if s.get("enabled") else "Paused"
                        st.markdown(f'<span class="{badge}">{label}</span>', unsafe_allow_html=True)
                    with c4:
                        if st.button("Remove", key=f"del_{s['id']}"):
                            api_request("DELETE", f"/schedules/reports/{s['id']}")
                            st.rerun()
            else:
                st.info("No schedules for this account.")
        else:
            st.info("No schedules found.")


# ---------------------------------------------------------------------------
# DATA SOURCES
# ---------------------------------------------------------------------------

def data_sources_page():
    """Data import, platform connections, and templates."""
    st.markdown('<div class="page-header">Data Sources</div>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.markdown('<div class="page-desc">Select an account to import data or connect ad platforms.</div>', unsafe_allow_html=True)
        return

    client = st.session_state.selected_client
    client_id = client["id"]
    st.markdown(
        f'<div class="page-desc">Import data or connect ad platforms for <strong>{client["name"]}</strong>.</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["Upload File", "Connect Platforms", "Templates"])

    # ---- Upload ----
    with tab1:
        file_format = st.radio("File format", ["CSV", "Excel", "JSON"], horizontal=True)
        ext_map = {"CSV": ["csv"], "Excel": ["xlsx", "xls"], "JSON": ["json"]}
        uploaded = st.file_uploader(f"Choose a {file_format} file", type=ext_map[file_format], help="Campaign or metrics data")

        if uploaded is not None:
            try:
                if file_format == "CSV":
                    df = pd.read_csv(uploaded)
                elif file_format == "Excel":
                    df = pd.read_excel(uploaded)
                else:
                    df = pd.read_json(uploaded)

                st.success(f"Loaded {len(df)} rows and {len(df.columns)} columns")
                st.dataframe(df.head(10), use_container_width=True)

                # Column mapping
                st.markdown('<div class="section-title">Map your columns</div>', unsafe_allow_html=True)

                detected = "metrics" if "impressions" in [c.lower() for c in df.columns] else "campaigns"
                data_type = st.selectbox("Data type", ["Campaigns", "Metrics"], index=0 if detected == "campaigns" else 1)

                expected = {
                    "Campaigns": ["name", "objective", "start_date", "end_date", "budget", "channel"],
                    "Metrics": ["campaign_id", "date", "impressions", "clicks", "conversions", "spend", "revenue"],
                }

                mapping = {}
                cols_ui = st.columns(3)
                for i, exp_col in enumerate(expected[data_type]):
                    with cols_ui[i % 3]:
                        options = ["-- Skip --"] + list(df.columns)
                        default_idx = 0
                        for j, o in enumerate(options):
                            if o.lower().replace("_", "") == exp_col.lower().replace("_", ""):
                                default_idx = j
                                break
                        mapping[exp_col] = st.selectbox(exp_col, options, index=default_idx, key=f"map_{exp_col}")

                # Validation
                required = ["name", "channel"] if data_type == "Campaigns" else ["date", "impressions", "spend"]
                errors = [f"'{r}' must be mapped" for r in required if mapping.get(r) == "-- Skip --"]

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    st.success("Validation passed")

                if st.button("Upload data", type="primary", disabled=bool(errors)):
                    with st.spinner("Uploading..."):
                        rename = {v: k for k, v in mapping.items() if v != "-- Skip --"}
                        buf = io.StringIO()
                        df.rename(columns=rename).to_csv(buf, index=False)
                        buf.seek(0)
                        resp = api_request(
                            "POST", f"/ingest/csv/{client_id}",
                            files={"file": ("data.csv", buf.getvalue(), "text/csv")},
                        )
                    if resp and resp.status_code == 200:
                        st.success(f"Uploaded {resp.json().get('rows_processed', 0)} rows.")
                    else:
                        st.error("Upload failed. Please check your file and try again.")
            except Exception as e:
                st.error(f"Could not read file: {e}")

    # ---- Connect Platforms ----
    with tab2:
        conn_resp = api_request("GET", "/connections")
        connections = {}
        if conn_resp and conn_resp.status_code == 200:
            for c in conn_resp.json().get("connections", []):
                connections[c["platform"]] = c

        c1, c2 = st.columns(2)

        # Google Ads
        with c1:
            g = connections.get("google_ads", {})
            connected = g.get("connected", False)
            card_cls = "platform-card connected" if connected else "platform-card"
            st.markdown(f'<div class="{card_cls}"><div class="platform-name">Google Ads</div></div>', unsafe_allow_html=True)

            if connected:
                st.markdown(f'<span class="status-active">Connected</span>', unsafe_allow_html=True)
                if g.get("last_sync"):
                    st.caption(f"Last sync: {g['last_sync']}")
                if st.button("Disconnect", key="disc_g"):
                    api_request("DELETE", "/connections/google_ads")
                    st.rerun()
            else:
                if st.button("Connect via OAuth", key="oauth_g"):
                    resp = api_request("GET", "/connections/google-ads/auth-url")
                    if resp and resp.status_code == 200:
                        st.markdown(f"[Authorize Google Ads]({resp.json()['auth_url']})")
                    else:
                        detail = resp.json().get("detail", "") if resp else ""
                        st.warning(f"OAuth unavailable. {detail}")

                with st.expander("Enter credentials manually"):
                    with st.form("g_manual"):
                        g_dev = st.text_input("Developer Token", type="password")
                        g_cid = st.text_input("Client ID")
                        g_sec = st.text_input("Client Secret", type="password")
                        g_ref = st.text_input("Refresh Token", type="password")
                        g_lid = st.text_input("Login Customer ID")
                        if st.form_submit_button("Save"):
                            creds = {k: v for k, v in {
                                "developer_token": g_dev, "client_id": g_cid,
                                "client_secret": g_sec, "refresh_token": g_ref,
                                "login_customer_id": g_lid,
                            }.items() if v}
                            if creds:
                                resp = api_request("POST", "/connections/manual", json={"platform": "google_ads", "credentials": creds})
                                if resp and resp.status_code == 200:
                                    st.success("Saved")
                                    st.rerun()
                                else:
                                    st.error("Failed to save credentials")
                            else:
                                st.warning("Enter at least one credential")

        # Meta
        with c2:
            m = connections.get("meta", {})
            connected = m.get("connected", False)
            card_cls = "platform-card connected" if connected else "platform-card"
            st.markdown(f'<div class="{card_cls}"><div class="platform-name">Meta (Facebook / Instagram)</div></div>', unsafe_allow_html=True)

            if connected:
                st.markdown(f'<span class="status-active">Connected</span>', unsafe_allow_html=True)
                if m.get("last_sync"):
                    st.caption(f"Last sync: {m['last_sync']}")
                if st.button("Disconnect", key="disc_m"):
                    api_request("DELETE", "/connections/meta")
                    st.rerun()
            else:
                if st.button("Connect via OAuth", key="oauth_m"):
                    resp = api_request("GET", "/connections/meta/auth-url")
                    if resp and resp.status_code == 200:
                        st.markdown(f"[Authorize Meta Ads]({resp.json()['auth_url']})")
                    else:
                        detail = resp.json().get("detail", "") if resp else ""
                        st.warning(f"OAuth unavailable. {detail}")

                with st.expander("Enter credentials manually"):
                    with st.form("m_manual"):
                        m_aid = st.text_input("App ID")
                        m_sec = st.text_input("App Secret", type="password")
                        m_tok = st.text_input("Access Token", type="password")
                        if st.form_submit_button("Save"):
                            creds = {k: v for k, v in {
                                "app_id": m_aid, "app_secret": m_sec, "access_token": m_tok,
                            }.items() if v}
                            if creds:
                                resp = api_request("POST", "/connections/manual", json={"platform": "meta", "credentials": creds})
                                if resp and resp.status_code == 200:
                                    st.success("Saved")
                                    st.rerun()
                                else:
                                    st.error("Failed to save credentials")
                            else:
                                st.warning("Enter at least one credential")

    # ---- Templates ----
    with tab3:
        st.markdown("Download pre-formatted templates, fill them with your data, then upload.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">Campaign Template</div>', unsafe_allow_html=True)
            tpl = pd.DataFrame({
                "name": ["Summer Sale Campaign", "Brand Awareness"],
                "objective": ["conversions", "awareness"],
                "start_date": ["2024-01-01", "2024-01-15"],
                "end_date": ["2024-03-31", "2024-02-28"],
                "budget": [5000.00, 3000.00],
                "channel": ["google_ads", "meta"],
            })
            st.download_button("Download campaign template", tpl.to_csv(index=False), "campaign_template.csv", "text/csv", use_container_width=True)

        with c2:
            st.markdown('<div class="section-title">Metrics Template</div>', unsafe_allow_html=True)
            tpl = pd.DataFrame({
                "campaign_id": ["camp_001", "camp_001", "camp_002"],
                "date": ["2024-01-01", "2024-01-02", "2024-01-01"],
                "impressions": [10000, 12000, 8000],
                "clicks": [500, 600, 350],
                "conversions": [25, 30, 15],
                "spend": [150.00, 180.00, 100.00],
                "revenue": [500.00, 600.00, 300.00],
            })
            st.download_button("Download metrics template", tpl.to_csv(index=False), "metrics_template.csv", "text/csv", use_container_width=True)


# ---------------------------------------------------------------------------
# SETTINGS (Admin)
# ---------------------------------------------------------------------------

def settings_page():
    """Admin settings: clients, users, system health, audit."""
    st.markdown('<div class="page-header">Settings</div>', unsafe_allow_html=True)

    if st.session_state.user.get("role") != "admin":
        st.error("You don't have permission to access this page.")
        return

    st.markdown('<div class="page-desc">Manage accounts, team members, and system configuration.</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Accounts", "Team", "System", "Activity"])

    # ---- Accounts ----
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            resp = api_request("GET", "/ingest/clients")
            if resp and resp.status_code == 200:
                clients = resp.json().get("clients", [])
                seen = set()
                unique = []
                for c in clients:
                    if c["name"] not in seen:
                        seen.add(c["name"])
                        unique.append(c)
                if unique:
                    cdf = pd.DataFrame(unique)
                    show = [c for c in ["name", "industry", "budget", "budget_currency", "status"] if c in cdf.columns]
                    st.dataframe(cdf[show], hide_index=True, use_container_width=True, column_config={
                        "name": st.column_config.TextColumn("Account"),
                        "industry": st.column_config.TextColumn("Industry"),
                        "budget": st.column_config.NumberColumn("Budget", format="$%.0f"),
                        "budget_currency": st.column_config.TextColumn("Currency"),
                        "status": st.column_config.TextColumn("Status"),
                    })
                else:
                    st.info("No accounts yet.")

        with c2:
            st.markdown('<div class="section-title">Add Account</div>', unsafe_allow_html=True)
            with st.form("add_client"):
                name = st.text_input("Account name", placeholder="Acme Corp")
                industry = st.selectbox("Industry", ["E-commerce", "Retail", "Healthcare", "Finance", "SaaS", "Travel", "Other"])
                budget = st.number_input("Monthly budget", min_value=0, value=10000)
                currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])
                if st.form_submit_button("Add account", use_container_width=True):
                    if name:
                        resp = api_request("POST", "/ingest/clients", json={
                            "name": name, "industry": industry,
                            "budget": budget, "budget_currency": currency,
                            "data_retention_days": 365,
                        })
                        if resp and resp.status_code == 201:
                            st.success(f"Account '{name}' created.")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Failed to create account") if resp else "Connection error")
                    else:
                        st.warning("Please enter an account name.")

    # ---- Team ----
    with tab2:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown('<div class="section-title">Team Members</div>', unsafe_allow_html=True)
            try:
                from src.graph.client import get_neo4j_client
                neo4j = get_neo4j_client()
                result = neo4j.execute_query("""
                    MATCH (u:User)
                    RETURN u.name as name, u.email as email, u.role as role
                    ORDER BY u.name
                """)
                if result:
                    st.dataframe(pd.DataFrame([dict(r) for r in result]), hide_index=True, use_container_width=True)
                else:
                    st.info("No team members found.")
            except Exception:
                st.warning("Could not load team members.")

        with c2:
            st.markdown('<div class="section-title">Invite Member</div>', unsafe_allow_html=True)
            with st.form("add_user"):
                uname = st.text_input("Full name", placeholder="Jane Smith")
                uemail = st.text_input("Email", placeholder="jane@company.com")
                upass = st.text_input("Password", type="password")
                urole = st.selectbox("Role", ["analyst", "manager", "admin"])

                # Client assignment
                client_resp = api_request("GET", "/ingest/clients")
                opts = []
                if client_resp and client_resp.status_code == 200:
                    seen = set()
                    for c in client_resp.json().get("clients", []):
                        if c["name"] not in seen:
                            seen.add(c["name"])
                            opts.append((c["id"], c["name"]))
                assigned = st.multiselect(
                    "Assign to accounts",
                    options=[o[0] for o in opts],
                    format_func=lambda x: next((o[1] for o in opts if o[0] == x), x),
                )

                if st.form_submit_button("Add member", use_container_width=True):
                    if uname and uemail and upass:
                        resp = api_request("POST", "/auth/register", json={
                            "name": uname, "email": uemail,
                            "password": upass, "role": urole,
                            "client_ids": assigned,
                        })
                        if resp and resp.status_code == 201:
                            st.success(f"'{uname}' added.")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Failed to add member") if resp else "Connection error")
                    else:
                        st.warning("Please fill in all fields.")

    # ---- System ----
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">API Health</div>', unsafe_allow_html=True)
            try:
                health_resp = requests.get(f"{API_BASE_URL.replace('/api', '')}/health", timeout=5)
                if health_resp.status_code == 200:
                    h = health_resp.json()
                    badge = "status-active" if h.get("status") == "healthy" else "status-paused"
                    st.markdown(f'<span class="{badge}">{h.get("status", "unknown").title()}</span>', unsafe_allow_html=True)
                    st.caption(f"Database: {h.get('neo4j', 'unknown')}")
                else:
                    st.markdown('<span class="status-error">Unreachable</span>', unsafe_allow_html=True)
            except Exception:
                st.markdown('<span class="status-error">Unreachable</span>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">Database</div>', unsafe_allow_html=True)
            try:
                from src.graph.client import get_neo4j_client
                neo4j = get_neo4j_client()
                if neo4j.verify_connectivity():
                    st.markdown('<span class="status-active">Connected</span>', unsafe_allow_html=True)
                    result = neo4j.execute_query("""
                        MATCH (n)
                        RETURN labels(n)[0] as label, count(*) as count
                        ORDER BY count DESC
                    """)
                    if result:
                        for r in result:
                            st.caption(f"{r['label']}: {r['count']:,}")
                else:
                    st.markdown('<span class="status-error">Disconnected</span>', unsafe_allow_html=True)
            except Exception:
                st.markdown('<span class="status-error">Error</span>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="section-title">AI Model</div>', unsafe_allow_html=True)
            st.text_input("Model", value="claude-sonnet-4-20250514", disabled=True)
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if api_key and len(api_key) > 10:
                st.markdown('<span class="status-active">API key configured</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-error">API key missing</span>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">Integrations</div>', unsafe_allow_html=True)
            slack = os.getenv("SLACK_WEBHOOK_URL", "")
            sg = os.getenv("SENDGRID_API_KEY", "")
            st.caption(f"Slack: {'Configured' if slack else 'Not configured'}")
            st.caption(f"Email (SendGrid): {'Configured' if sg else 'Not configured'}")

    # ---- Activity ----
    with tab4:
        st.markdown('<div class="section-title">Recent Activity</div>', unsafe_allow_html=True)
        try:
            from src.graph.client import get_neo4j_client
            neo4j = get_neo4j_client()
            result = neo4j.execute_query("""
                MATCH (a:AuditLog)
                RETURN a.timestamp as timestamp, a.user_email as user,
                       a.action as action, a.details as details
                ORDER BY a.timestamp DESC
                LIMIT 50
            """)
            if result:
                st.dataframe(pd.DataFrame([dict(r) for r in result]), hide_index=True, use_container_width=True)
            else:
                st.info("No activity recorded yet.")
        except Exception:
            st.info("Activity log unavailable.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not st.session_state.token:
        login_page()
        return

    page = sidebar()

    if page == "Home":
        home_page()
    elif page == "Ask":
        ask_page()
    elif page == "Reports":
        reports_page()
    elif page == "Data Sources":
        data_sources_page()
    elif page == "Settings":
        settings_page()


if __name__ == "__main__":
    main()
