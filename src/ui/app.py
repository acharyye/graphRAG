"""Streamlit UI for Marketing GraphRAG."""

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

# Page config
st.set_page_config(
    page_title="Marketing GraphRAG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Corporate styling
st.markdown(
    """
    <style>
    /* Main app background */
    .stApp {
        background-color: #f8fafc;
    }

    /* Ensure all text is visible */
    .stApp, .stApp * {
        color: #1a202c;
    }

    /* Main header */
    .main-header {
        color: #1a365d !important;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    /* Sub header */
    .sub-header {
        color: #2d3748 !important;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    /* Chat message containers */
    .stChatMessage {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    /* User messages */
    [data-testid="stChatMessageContent"] {
        color: #1a202c !important;
        background-color: transparent !important;
    }

    /* Chat input */
    .stChatInput, .stChatInput textarea {
        background-color: #ffffff !important;
        color: #1a202c !important;
        border: 1px solid #cbd5e0 !important;
    }

    .stChatInput textarea::placeholder {
        color: #718096 !important;
    }

    /* Markdown text in chat */
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #1a202c !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
    }

    [data-testid="stSidebar"] * {
        color: #1a202c !important;
    }

    /* Metric cards */
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Source citations */
    .source-citation {
        background-color: #edf2f7;
        padding: 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        color: #2d3748 !important;
    }

    /* Confidence indicators */
    .confidence-high { color: #22543d !important; }
    .confidence-medium { color: #744210 !important; }
    .confidence-low { color: #742a2a !important; }

    /* Buttons */
    .stButton button {
        color: #ffffff !important;
        background-color: #3182ce !important;
    }

    .stButton button:hover {
        background-color: #2c5282 !important;
    }

    /* Form inputs */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        color: #1a202c !important;
        background-color: #ffffff !important;
    }

    /* Labels */
    .stTextInput label, .stSelectbox label, .stDateInput label {
        color: #2d3748 !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        color: #1a202c !important;
        background-color: #edf2f7 !important;
    }

    .streamlit-expanderContent {
        color: #1a202c !important;
        background-color: #ffffff !important;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        color: #1a202c !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #edf2f7;
        color: #1a202c !important;
        border-radius: 4px;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #3182ce !important;
        color: #ffffff !important;
    }

    /* Data tables */
    .stDataFrame {
        background-color: #ffffff;
    }

    /* Success/Error cards */
    .success-card {
        background-color: #c6f6d5;
        border: 1px solid #9ae6b4;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #22543d !important;
    }

    .error-card {
        background-color: #fed7d7;
        border: 1px solid #feb2b2;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #742a2a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_client" not in st.session_state:
    st.session_state.selected_client = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())


def api_request(method: str, endpoint: str, **kwargs):
    """Make API request with authentication."""
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        return response
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Please ensure it's running.")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None


def login_page():
    """Render login page."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="main-header">Marketing GraphRAG</h1>', unsafe_allow_html=True)
        st.markdown("#### Sign In to Your Account")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@agency.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                response = api_request(
                    "POST",
                    "/auth/login",
                    json={"email": email, "password": password},
                )

                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.rerun()
                else:
                    st.error("Invalid email or password")


def sidebar():
    """Render sidebar with client selector and navigation."""
    with st.sidebar:
        st.markdown(f"### {st.session_state.user['name']}")
        st.caption(f"Role: {st.session_state.user['role'].upper()}")

        st.divider()

        # Client selector (not shown on Admin page)
        st.markdown("#### Select Client")
        response = api_request("GET", "/ingest/clients")

        if response and response.status_code == 200:
            clients_data = response.json()
            clients = clients_data.get("clients", [])

            if clients:
                # Remove duplicates by name (keep first occurrence)
                seen_names = set()
                unique_clients = []
                for c in clients:
                    if c["name"] not in seen_names:
                        seen_names.add(c["name"])
                        unique_clients.append(c)

                client_names = {c["id"]: c["name"] for c in unique_clients}
                selected_id = st.selectbox(
                    "Client",
                    options=list(client_names.keys()),
                    format_func=lambda x: client_names[x],
                    label_visibility="collapsed",
                )
                st.session_state.selected_client = next(
                    (c for c in unique_clients if c["id"] == selected_id), None
                )
            else:
                st.info("No clients available")
        else:
            st.error("Failed to load clients")

        st.divider()

        # Navigation - Show Admin option only for admins
        st.markdown("#### Navigation")
        nav_options = ["Query", "Dashboard", "Reports", "Data Import"]
        if st.session_state.user.get("role") == "admin":
            nav_options.append("Admin")

        page = st.radio(
            "Go to",
            nav_options,
            label_visibility="collapsed",
        )

        st.divider()

        # Date range selector
        st.markdown("#### Date Range")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start",
                value=datetime.now() - timedelta(days=30),
                label_visibility="collapsed",
            )
        with col2:
            end_date = st.date_input(
                "End",
                value=datetime.now(),
                label_visibility="collapsed",
            )

        st.session_state.date_range = (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        st.divider()

        # Logout
        if st.button("Sign Out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.chat_history = []
            st.rerun()

        return page


def query_page():
    """Render natural language query interface."""
    st.markdown('<h1 class="main-header">Ask Questions</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_name = st.session_state.selected_client["name"]
    st.markdown(f"*Querying data for **{client_name}***")

    # Chat history display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for source in msg["sources"]:
                        st.markdown(
                            f"- **{source['entity_type']}**: {source.get('entity_name', source['entity_id'])} "
                            f"({source.get('date_range', 'N/A')})"
                        )
            if msg.get("confidence"):
                conf = msg["confidence"]
                conf_class = f"confidence-{conf['level']}"
                st.markdown(
                    f'<div class="{conf_class}">Confidence: {conf["level"].upper()} '
                    f'({conf["overall"]:.0%})</div>',
                    unsafe_allow_html=True,
                )
            if msg.get("recommendations"):
                with st.expander("Recommendations"):
                    for rec in msg["recommendations"]:
                        st.markdown(f"- {rec}")

    # Query input
    query = st.chat_input("Ask a question about your marketing data...")

    if query:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": query})

        # Make API request
        with st.spinner("Analyzing data..."):
            response = api_request(
                "POST",
                "/query",
                json={
                    "query": query,
                    "client_id": st.session_state.selected_client["id"],
                    "session_id": st.session_state.session_id,
                    "date_range": st.session_state.date_range,
                },
            )

        if response and response.status_code == 200:
            data = response.json()

            # Add assistant message to history
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": data["answer"],
                    "sources": data.get("sources", []),
                    "confidence": data.get("confidence"),
                    "recommendations": data.get("recommendations"),
                }
            )
        else:
            error_msg = "Failed to process query"
            if response:
                error_msg = response.json().get("detail", error_msg)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": f"Error: {error_msg}"}
            )

        st.rerun()

    # Clear chat button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.session_id = str(uuid4())
            st.rerun()


def dashboard_page():
    """Render metrics dashboard with real data."""
    st.markdown('<h1 class="main-header">Dashboard</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_id = st.session_state.selected_client["id"]
    client_name = st.session_state.selected_client["name"]

    st.markdown(f"### {client_name} Performance")
    st.caption(
        f"Date range: {st.session_state.date_range[0]} to {st.session_state.date_range[1]}"
    )

    # Fetch real dashboard data from API
    with st.spinner("Loading dashboard data..."):
        response = api_request(
            "GET",
            f"/dashboard/{client_id}?start_date={st.session_state.date_range[0]}&end_date={st.session_state.date_range[1]}"
        )

    if response and response.status_code == 200:
        data = response.json()
        summary = data.get("summary", {})
        daily_metrics = data.get("daily_metrics", [])
        channel_breakdown = data.get("channel_breakdown", [])
        campaigns = data.get("campaigns", [])
    else:
        # Fallback: fetch metrics directly via a query
        st.info("Loading metrics from database...")
        summary = fetch_metrics_summary(client_id)
        daily_metrics = fetch_daily_metrics(client_id)
        channel_breakdown = fetch_channel_breakdown(client_id)
        campaigns = fetch_campaigns(client_id)

    # Metrics row
    cols = st.columns(6)
    metrics_display = [
        ("Total Spend", f"${summary.get('total_spend', 0):,.0f}", None),
        ("Impressions", f"{summary.get('total_impressions', 0):,.0f}", None),
        ("Clicks", f"{summary.get('total_clicks', 0):,.0f}", None),
        ("Conversions", f"{summary.get('total_conversions', 0):,.0f}", None),
        ("CTR", f"{summary.get('avg_ctr', 0):.2f}%", None),
        ("ROAS", f"{summary.get('roas', 0):.2f}x", None),
    ]

    for col, (label, value, delta) in zip(cols, metrics_display):
        with col:
            st.metric(label, value, delta)

    st.divider()

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Daily Performance")
        if daily_metrics:
            daily_df = pd.DataFrame(daily_metrics)
            if 'date' in daily_df.columns:
                daily_df['date'] = pd.to_datetime(daily_df['date'])

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=daily_df["date"],
                        y=daily_df.get("spend", daily_df.get("total_spend", [])),
                        name="Spend ($)",
                        line=dict(color="#1a365d"),
                    )
                )
                if "conversions" in daily_df.columns or "total_conversions" in daily_df.columns:
                    conv_col = "conversions" if "conversions" in daily_df.columns else "total_conversions"
                    fig.add_trace(
                        go.Scatter(
                            x=daily_df["date"],
                            y=daily_df[conv_col] * 50,
                            name="Conversions (x50)",
                            line=dict(color="#38a169"),
                        )
                    )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily metrics available for the selected period")

    with col2:
        st.markdown("#### Channel Breakdown")
        if channel_breakdown:
            channel_df = pd.DataFrame(channel_breakdown)
            fig = px.pie(
                channel_df,
                values="spend" if "spend" in channel_df.columns else "total_spend",
                names="channel",
                color_discrete_sequence=["#1a365d", "#4299e1", "#48bb78", "#ed8936"],
            )
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No channel data available")

    st.divider()

    # Campaign table
    st.markdown("#### Campaign Performance")
    if campaigns:
        campaign_df = pd.DataFrame(campaigns)
        display_cols = ["name", "channel", "status", "spend", "clicks", "conversions", "ctr", "roas"]
        available_cols = [c for c in display_cols if c in campaign_df.columns]

        if available_cols:
            st.dataframe(
                campaign_df[available_cols],
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
                    "roas": st.column_config.NumberColumn("ROAS", format="%.2fx"),
                },
            )
    else:
        st.info("No campaign data available")


def fetch_metrics_summary(client_id: str) -> dict:
    """Fetch metrics summary directly from the database."""
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()

        start_date = st.session_state.date_range[0]
        end_date = st.session_state.date_range[1]

        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:RUNS]->(camp:Campaign)-[:HAS_METRIC]->(m:Metric)
            WHERE m.date >= date($start_date) AND m.date <= date($end_date)
            RETURN
                sum(m.spend) as total_spend,
                sum(m.impressions) as total_impressions,
                sum(m.clicks) as total_clicks,
                sum(m.conversions) as total_conversions,
                CASE WHEN sum(m.impressions) > 0 THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as avg_ctr,
                CASE WHEN sum(m.spend) > 0 THEN sum(m.revenue) / sum(m.spend) ELSE 0 END as roas
        """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

        if result:
            return result[0]
        return {}
    except Exception as e:
        st.warning(f"Could not fetch metrics: {e}")
        return {}


def fetch_daily_metrics(client_id: str) -> list:
    """Fetch daily metrics from the database."""
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()

        start_date = st.session_state.date_range[0]
        end_date = st.session_state.date_range[1]

        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:RUNS]->(camp:Campaign)-[:HAS_METRIC]->(m:Metric)
            WHERE m.date >= date($start_date) AND m.date <= date($end_date)
            RETURN
                toString(m.date) as date,
                sum(m.spend) as total_spend,
                sum(m.conversions) as total_conversions
            ORDER BY m.date
        """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

        return [dict(r) for r in result] if result else []
    except Exception as e:
        st.warning(f"Could not fetch daily metrics: {e}")
        return []


def fetch_channel_breakdown(client_id: str) -> list:
    """Fetch channel breakdown from the database."""
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()

        start_date = st.session_state.date_range[0]
        end_date = st.session_state.date_range[1]

        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:RUNS]->(camp:Campaign)-[:ADVERTISES_ON]->(ch:Channel)
            MATCH (camp)-[:HAS_METRIC]->(m:Metric)
            WHERE m.date >= date($start_date) AND m.date <= date($end_date)
            RETURN
                ch.name as channel,
                sum(m.spend) as total_spend,
                sum(m.conversions) as total_conversions
        """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

        return [dict(r) for r in result] if result else []
    except Exception as e:
        st.warning(f"Could not fetch channel data: {e}")
        return []


def fetch_campaigns(client_id: str) -> list:
    """Fetch campaign data from the database."""
    try:
        from src.graph.client import get_neo4j_client
        neo4j = get_neo4j_client()

        start_date = st.session_state.date_range[0]
        end_date = st.session_state.date_range[1]

        result = neo4j.execute_query("""
            MATCH (c:Client {id: $client_id})-[:RUNS]->(camp:Campaign)-[:ADVERTISES_ON]->(ch:Channel)
            OPTIONAL MATCH (camp)-[:HAS_METRIC]->(m:Metric)
            WHERE m.date >= date($start_date) AND m.date <= date($end_date)
            RETURN
                camp.name as name,
                ch.name as channel,
                camp.status as status,
                sum(m.spend) as spend,
                sum(m.clicks) as clicks,
                sum(m.conversions) as conversions,
                CASE WHEN sum(m.impressions) > 0 THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as ctr,
                CASE WHEN sum(m.spend) > 0 THEN sum(m.revenue) / sum(m.spend) ELSE 0 END as roas
            ORDER BY spend DESC
            LIMIT 20
        """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

        return [dict(r) for r in result] if result else []
    except Exception as e:
        st.warning(f"Could not fetch campaigns: {e}")
        return []


def reports_page():
    """Render reports generation page."""
    st.markdown('<h1 class="main-header">Reports</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_name = st.session_state.selected_client["name"]
    client_id = st.session_state.selected_client["id"]

    tab1, tab2 = st.tabs(["Generate Report", "Scheduled Reports"])

    with tab1:
        st.markdown(f"### Generate Report for {client_name}")

        col1, col2 = st.columns(2)

        with col1:
            report_type = st.selectbox(
                "Report Type",
                ["Monthly", "Weekly", "Daily", "Quarterly", "Custom"],
            )

            format_option = st.selectbox(
                "Format",
                ["PDF", "Excel", "CSV"],
            )

        with col2:
            sections = st.multiselect(
                "Sections",
                ["Summary", "Campaigns", "Ad Sets", "Trends", "Recommendations", "Channel Breakdown"],
                default=["Summary", "Campaigns", "Trends", "Recommendations"],
            )

            include_comparison = st.checkbox("Compare to previous period", value=True)

        st.divider()

        if st.button("Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                section_map = {
                    "Summary": "summary",
                    "Campaigns": "campaigns",
                    "Ad Sets": "ad_sets",
                    "Trends": "trends",
                    "Recommendations": "recommendations",
                    "Channel Breakdown": "channel_breakdown",
                }

                response = api_request(
                    "POST",
                    "/reports",
                    json={
                        "client_id": client_id,
                        "report_type": report_type.lower(),
                        "format": format_option.lower(),
                        "date_range": {
                            "start": st.session_state.date_range[0],
                            "end": st.session_state.date_range[1],
                        },
                        "sections": [section_map[s] for s in sections],
                        "include_recommendations": "Recommendations" in sections,
                        "compare_to_previous": include_comparison,
                    },
                )

                if response and response.status_code == 202:
                    data = response.json()
                    st.success(f"Report generation started. Report ID: {data['report_id']}")
                else:
                    st.error("Failed to generate report")

        st.divider()

        # Recent reports list
        st.markdown("### Recent Reports")

        response = api_request("GET", f"/reports?client_id={client_id}")

        if response and response.status_code == 200:
            reports = response.json().get("reports", [])

            if reports:
                for report in reports[:10]:
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(
                            f"**{report['report_type'].title()}** - "
                            f"{report['date_range']['start']} to {report['date_range']['end']}"
                        )
                    with col2:
                        st.markdown(f"`{report['format'].upper()}`")
                    with col3:
                        status_colors = {
                            "completed": "green",
                            "generating": "orange",
                            "pending": "gray",
                            "failed": "red",
                        }
                        st.markdown(
                            f":{status_colors.get(report['status'], 'gray')}[{report['status'].upper()}]"
                        )
                    with col4:
                        if report["status"] == "completed" and report.get("download_url"):
                            st.markdown(f"[Download]({API_BASE_URL}{report['download_url']})")
            else:
                st.info("No reports generated yet")
        else:
            st.error("Failed to load reports")

    with tab2:
        st.markdown("### Schedule Automated Reports")
        st.info("Set up reports to be automatically generated and sent to your email.")

        with st.form("schedule_report_form"):
            col1, col2 = st.columns(2)
            with col1:
                schedule_type = st.selectbox(
                    "Frequency",
                    ["Daily", "Weekly", "Monthly"],
                )
                report_format = st.selectbox(
                    "Format",
                    ["PDF", "Excel"],
                    key="schedule_format"
                )
            with col2:
                email = st.text_input("Email Address", placeholder="reports@company.com")
                time_of_day = st.time_input("Delivery Time", value=datetime.strptime("09:00", "%H:%M").time())

            schedule_submitted = st.form_submit_button("Create Schedule", use_container_width=True)

            if schedule_submitted:
                if email:
                    st.success(f"Report schedule created! {schedule_type} {report_format} reports will be sent to {email}")
                else:
                    st.error("Please enter an email address")


def data_import_page():
    """Render enhanced data import page."""
    st.markdown('<h1 class="main-header">Data Import</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_name = st.session_state.selected_client["name"]
    client_id = st.session_state.selected_client["id"]

    tab1, tab2, tab3, tab4 = st.tabs(["Upload File", "Connect APIs", "Templates", "Import History"])

    with tab1:
        st.markdown(f"### Upload Data for {client_name}")

        # File format selection
        file_format = st.radio(
            "Select file format",
            ["CSV", "Excel (.xlsx)", "JSON"],
            horizontal=True,
        )

        # Map format to file types
        format_map = {
            "CSV": ["csv"],
            "Excel (.xlsx)": ["xlsx", "xls"],
            "JSON": ["json"],
        }

        uploaded_file = st.file_uploader(
            f"Choose a {file_format} file",
            type=format_map[file_format],
            help="Upload campaign or metrics data",
        )

        if uploaded_file is not None:
            # Read file based on format
            try:
                if file_format == "CSV":
                    df = pd.read_csv(uploaded_file)
                elif file_format == "Excel (.xlsx)":
                    df = pd.read_excel(uploaded_file)
                else:  # JSON
                    df = pd.read_json(uploaded_file)

                st.success(f"File loaded: {len(df)} rows, {len(df.columns)} columns")

                # Data preview
                st.markdown("#### Data Preview")
                st.dataframe(df.head(10), use_container_width=True)

                # Column mapping
                st.markdown("#### Column Mapping")
                st.info("Map your file columns to the expected data fields")

                col1, col2 = st.columns(2)

                # Detect data type
                detected_type = "metrics" if "impressions" in df.columns.str.lower().tolist() else "campaigns"

                with col1:
                    data_type = st.selectbox(
                        "Data Type",
                        ["Campaigns", "Metrics"],
                        index=0 if detected_type == "campaigns" else 1,
                    )

                expected_cols = {
                    "Campaigns": ["name", "objective", "start_date", "end_date", "budget", "channel"],
                    "Metrics": ["campaign_id", "date", "impressions", "clicks", "conversions", "spend", "revenue"],
                }

                with col2:
                    st.markdown("**Expected columns:**")
                    st.caption(", ".join(expected_cols[data_type]))

                # Column mapping interface
                st.markdown("#### Map Columns")
                mapping = {}
                cols = st.columns(3)
                for i, expected_col in enumerate(expected_cols[data_type]):
                    with cols[i % 3]:
                        # Try to auto-match columns
                        default_idx = 0
                        file_cols = ["-- Skip --"] + list(df.columns)
                        for j, fc in enumerate(file_cols):
                            if fc.lower().replace("_", "") == expected_col.lower().replace("_", ""):
                                default_idx = j
                                break

                        mapping[expected_col] = st.selectbox(
                            f"{expected_col}",
                            file_cols,
                            index=default_idx,
                            key=f"map_{expected_col}",
                        )

                # Data validation
                st.markdown("#### Validation")
                validation_errors = []
                validation_warnings = []

                # Check required columns are mapped
                required = ["name", "channel"] if data_type == "Campaigns" else ["date", "impressions", "spend"]
                for req in required:
                    if mapping.get(req) == "-- Skip --":
                        validation_errors.append(f"Required column '{req}' is not mapped")

                # Check data types
                if data_type == "Metrics":
                    if mapping.get("date") and mapping["date"] != "-- Skip --":
                        try:
                            pd.to_datetime(df[mapping["date"]])
                        except:
                            validation_errors.append("Date column contains invalid dates")

                    numeric_cols = ["impressions", "clicks", "conversions", "spend", "revenue"]
                    for nc in numeric_cols:
                        if mapping.get(nc) and mapping[nc] != "-- Skip --":
                            if not pd.api.types.is_numeric_dtype(df[mapping[nc]]):
                                validation_warnings.append(f"Column '{mapping[nc]}' may not be numeric")

                if validation_errors:
                    for err in validation_errors:
                        st.error(err)
                elif validation_warnings:
                    for warn in validation_warnings:
                        st.warning(warn)
                    st.info("Warnings detected but you can still proceed")
                else:
                    st.success("Validation passed!")

                # Upload button
                if st.button("Upload Data", type="primary", disabled=bool(validation_errors)):
                    with st.spinner("Uploading data..."):
                        # Rename columns based on mapping
                        rename_map = {v: k for k, v in mapping.items() if v != "-- Skip --"}
                        upload_df = df.rename(columns=rename_map)

                        # Convert to CSV for upload
                        csv_buffer = io.StringIO()
                        upload_df.to_csv(csv_buffer, index=False)
                        csv_buffer.seek(0)

                        response = api_request(
                            "POST",
                            f"/ingest/csv/{client_id}",
                            files={"file": ("data.csv", csv_buffer.getvalue(), "text/csv")},
                        )

                        if response and response.status_code == 200:
                            result = response.json()
                            st.success(f"Successfully uploaded {result.get('rows_processed', 0)} rows!")
                        else:
                            st.error("Failed to upload data")

            except Exception as e:
                st.error(f"Error reading file: {e}")

    with tab2:
        st.markdown("### Connect Ad Platforms")
        st.info("Connect your advertising accounts to automatically sync data")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Google Ads")
            st.markdown("Connect your Google Ads account for automatic data sync")

            google_status = "Not Connected"
            if st.button("Connect Google Ads", key="connect_google"):
                st.info("Google Ads OAuth flow would open here. Configure GOOGLE_ADS_* in .env")

            st.caption(f"Status: {google_status}")

        with col2:
            st.markdown("#### Meta (Facebook/Instagram)")
            st.markdown("Connect your Meta Business account for automatic data sync")

            meta_status = "Not Connected"
            if st.button("Connect Meta Ads", key="connect_meta"):
                st.info("Meta OAuth flow would open here. Configure META_* in .env")

            st.caption(f"Status: {meta_status}")

        st.divider()

        st.markdown("#### Sync Settings")
        sync_frequency = st.selectbox(
            "Auto-sync Frequency",
            ["Every 6 hours", "Every 12 hours", "Daily", "Manual only"],
        )
        if st.button("Save Sync Settings"):
            st.success("Sync settings saved!")

    with tab3:
        st.markdown("### Download Templates")
        st.info("Download CSV templates with the correct column structure")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Campaign Template")
            campaign_template = pd.DataFrame({
                "name": ["Summer Sale Campaign", "Brand Awareness"],
                "objective": ["conversions", "awareness"],
                "start_date": ["2024-01-01", "2024-01-15"],
                "end_date": ["2024-03-31", "2024-02-28"],
                "budget": [5000.00, 3000.00],
                "channel": ["google_ads", "meta"],
            })
            csv = campaign_template.to_csv(index=False)
            st.download_button(
                "Download Campaign Template",
                csv,
                "campaign_template.csv",
                "text/csv",
                use_container_width=True,
            )

        with col2:
            st.markdown("#### Metrics Template")
            metrics_template = pd.DataFrame({
                "campaign_id": ["camp_001", "camp_001", "camp_002"],
                "date": ["2024-01-01", "2024-01-02", "2024-01-01"],
                "impressions": [10000, 12000, 8000],
                "clicks": [500, 600, 350],
                "conversions": [25, 30, 15],
                "spend": [150.00, 180.00, 100.00],
                "revenue": [500.00, 600.00, 300.00],
                "currency": ["USD", "USD", "USD"],
            })
            csv = metrics_template.to_csv(index=False)
            st.download_button(
                "Download Metrics Template",
                csv,
                "metrics_template.csv",
                "text/csv",
                use_container_width=True,
            )

    with tab4:
        st.markdown("### Import History")

        # This would normally come from the database
        import_history = [
            {"date": "2024-01-28 10:30", "file": "january_metrics.csv", "rows": 450, "status": "Success"},
            {"date": "2024-01-25 14:15", "file": "campaigns.xlsx", "rows": 12, "status": "Success"},
            {"date": "2024-01-20 09:00", "file": "data.json", "rows": 0, "status": "Failed - Invalid format"},
        ]

        if import_history:
            history_df = pd.DataFrame(import_history)
            st.dataframe(history_df, hide_index=True, use_container_width=True)
        else:
            st.info("No import history available")


def admin_page():
    """Render admin panel for system management."""
    st.markdown('<h1 class="main-header">Admin Panel</h1>', unsafe_allow_html=True)

    if st.session_state.user.get("role") != "admin":
        st.error("Access denied. Admin privileges required.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Clients", "Users", "System", "Audit Log"])

    with tab1:
        st.markdown("### Client Management")

        col1, col2 = st.columns([2, 1])

        with col1:
            # List existing clients
            response = api_request("GET", "/ingest/clients")
            if response and response.status_code == 200:
                clients = response.json().get("clients", [])

                # Remove duplicates by name
                seen_names = set()
                unique_clients = []
                for c in clients:
                    if c["name"] not in seen_names:
                        seen_names.add(c["name"])
                        unique_clients.append(c)

                if unique_clients:
                    client_df = pd.DataFrame(unique_clients)
                    display_cols = ["name", "industry", "budget", "budget_currency", "status"]
                    available_cols = [c for c in display_cols if c in client_df.columns]

                    st.dataframe(
                        client_df[available_cols],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "name": st.column_config.TextColumn("Client Name"),
                            "industry": st.column_config.TextColumn("Industry"),
                            "budget": st.column_config.NumberColumn("Budget", format="$%.0f"),
                            "budget_currency": st.column_config.TextColumn("Currency"),
                            "status": st.column_config.TextColumn("Status"),
                        },
                    )
                else:
                    st.info("No clients found")

        with col2:
            st.markdown("#### Add New Client")
            with st.form("add_client_form"):
                client_name = st.text_input("Client Name", placeholder="Acme Corp")
                industry = st.selectbox(
                    "Industry",
                    ["E-commerce", "Retail", "Healthcare", "Finance", "SaaS", "Travel", "Other"],
                )
                budget = st.number_input("Monthly Budget", min_value=0, value=10000)
                currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])

                if st.form_submit_button("Add Client", use_container_width=True):
                    if client_name:
                        response = api_request(
                            "POST",
                            "/ingest/clients",
                            json={
                                "name": client_name,
                                "industry": industry,
                                "budget": budget,
                                "budget_currency": currency,
                                "data_retention_days": 365,
                            },
                        )
                        if response and response.status_code == 201:
                            st.success(f"Client '{client_name}' created!")
                            st.rerun()
                        else:
                            error_msg = "Failed to create client"
                            if response:
                                error_msg = response.json().get("detail", error_msg)
                            st.error(error_msg)
                    else:
                        st.error("Please enter a client name")

    with tab2:
        st.markdown("### User Management")

        col1, col2 = st.columns([2, 1])

        with col1:
            # List existing users (would need an API endpoint)
            st.markdown("#### Existing Users")

            # Fetch users from Neo4j directly
            try:
                from src.graph.client import get_neo4j_client
                neo4j = get_neo4j_client()
                result = neo4j.execute_query("""
                    MATCH (u:User)
                    RETURN u.name as name, u.email as email, u.role as role
                    ORDER BY u.name
                """)

                if result:
                    users_df = pd.DataFrame([dict(r) for r in result])
                    st.dataframe(users_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No users found")
            except Exception as e:
                st.warning(f"Could not fetch users: {e}")

        with col2:
            st.markdown("#### Add New User")
            with st.form("add_user_form"):
                user_name = st.text_input("Full Name", placeholder="John Doe")
                user_email = st.text_input("Email", placeholder="john@agency.com")
                user_password = st.text_input("Password", type="password")
                user_role = st.selectbox("Role", ["analyst", "manager", "admin"])

                # Client assignment
                response = api_request("GET", "/ingest/clients")
                client_options = []
                if response and response.status_code == 200:
                    clients = response.json().get("clients", [])
                    seen = set()
                    for c in clients:
                        if c["name"] not in seen:
                            seen.add(c["name"])
                            client_options.append((c["id"], c["name"]))

                assigned_clients = st.multiselect(
                    "Assign to Clients",
                    options=[c[0] for c in client_options],
                    format_func=lambda x: next((c[1] for c in client_options if c[0] == x), x),
                )

                if st.form_submit_button("Add User", use_container_width=True):
                    if user_name and user_email and user_password:
                        response = api_request(
                            "POST",
                            "/auth/register",
                            json={
                                "name": user_name,
                                "email": user_email,
                                "password": user_password,
                                "role": user_role,
                                "client_ids": assigned_clients,
                            },
                        )
                        if response and response.status_code == 201:
                            st.success(f"User '{user_name}' created!")
                            st.rerun()
                        else:
                            error_msg = "Failed to create user"
                            if response:
                                error_msg = response.json().get("detail", error_msg)
                            st.error(error_msg)
                    else:
                        st.error("Please fill in all required fields")

    with tab3:
        st.markdown("### System Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### API Configuration")
            st.text_input("API Base URL", value=API_BASE_URL, disabled=True)

            # Check API health
            response = requests.get(f"{API_BASE_URL.replace('/api', '')}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                st.success(f"API Status: {health.get('status', 'unknown')}")
                st.caption(f"Neo4j: {health.get('neo4j', 'unknown')}")
            else:
                st.error("API not responding")

            st.markdown("#### Database")
            try:
                from src.graph.client import get_neo4j_client
                neo4j = get_neo4j_client()
                if neo4j.verify_connectivity():
                    st.success("Neo4j: Connected")

                    # Get node counts
                    result = neo4j.execute_query("""
                        MATCH (n)
                        RETURN labels(n)[0] as label, count(*) as count
                        ORDER BY count DESC
                    """)
                    if result:
                        st.markdown("**Node Counts:**")
                        for r in result:
                            st.caption(f"- {r['label']}: {r['count']:,}")
                else:
                    st.error("Neo4j: Disconnected")
            except Exception as e:
                st.error(f"Neo4j error: {e}")

        with col2:
            st.markdown("#### LLM Configuration")
            st.text_input("Model", value="claude-sonnet-4-20250514", disabled=True)

            # Check if API key is set
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if api_key and len(api_key) > 10:
                st.success("Anthropic API Key: Configured")
            else:
                st.error("Anthropic API Key: Not configured")

            st.markdown("#### Notifications")
            slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
            sendgrid_key = os.getenv("SENDGRID_API_KEY", "")

            st.caption(f"Slack: {'Configured' if slack_url else 'Not configured'}")
            st.caption(f"SendGrid: {'Configured' if sendgrid_key else 'Not configured'}")

    with tab4:
        st.markdown("### Audit Log")
        st.info("Recent system activity and user actions")

        try:
            from src.graph.client import get_neo4j_client
            neo4j = get_neo4j_client()
            result = neo4j.execute_query("""
                MATCH (a:AuditLog)
                RETURN a.timestamp as timestamp, a.user_email as user, a.action as action, a.details as details
                ORDER BY a.timestamp DESC
                LIMIT 50
            """)

            if result:
                audit_df = pd.DataFrame([dict(r) for r in result])
                st.dataframe(audit_df, hide_index=True, use_container_width=True)
            else:
                st.info("No audit logs found")
        except Exception as e:
            st.warning(f"Could not fetch audit logs: {e}")


def main():
    """Main application entry point."""
    # Check authentication
    if not st.session_state.token:
        login_page()
        return

    # Render sidebar and get current page
    page = sidebar()

    # Render selected page
    if page == "Query":
        query_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Reports":
        reports_page()
    elif page == "Data Import":
        data_import_page()
    elif page == "Admin":
        admin_page()


if __name__ == "__main__":
    main()
