"""Streamlit UI for Marketing GraphRAG."""

import os
import sys
from datetime import datetime, timedelta
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
    .stApp {
        background-color: #f8fafc;
    }
    .main-header {
        color: #1a365d;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .source-citation {
        background-color: #edf2f7;
        padding: 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    .confidence-high { color: #22543d; }
    .confidence-medium { color: #744210; }
    .confidence-low { color: #742a2a; }
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
        response = requests.request(method, url, headers=headers, **kwargs)
        return response
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Please ensure it's running.")
        return None


def login_page():
    """Render login page."""
    st.markdown('<h1 class="main-header">Marketing GraphRAG</h1>', unsafe_allow_html=True)
    st.markdown("### Sign In")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="admin@agency.com")
        password = st.text_input("Password", type="password", placeholder="password123")
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
        st.caption(f"Role: {st.session_state.user['role']}")

        st.divider()

        # Client selector
        st.markdown("#### Select Client")
        response = api_request("GET", "/ingest/clients")

        if response and response.status_code == 200:
            clients_data = response.json()
            clients = clients_data.get("clients", [])

            if clients:
                client_names = {c["id"]: c["name"] for c in clients}
                selected_id = st.selectbox(
                    "Client",
                    options=list(client_names.keys()),
                    format_func=lambda x: client_names[x],
                    label_visibility="collapsed",
                )
                st.session_state.selected_client = next(
                    (c for c in clients if c["id"] == selected_id), None
                )
            else:
                st.info("No clients available")
        else:
            st.error("Failed to load clients")

        st.divider()

        # Navigation
        st.markdown("#### Navigation")
        page = st.radio(
            "Go to",
            ["Query", "Dashboard", "Reports", "Data Upload"],
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
    """Render metrics dashboard."""
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

    # Fetch dashboard data (mock for now since we need to add a dedicated endpoint)
    # In production, this would call /api/dashboard/{client_id}

    # Mock data for demonstration
    summary = {
        "total_spend": 25000,
        "total_impressions": 500000,
        "total_clicks": 15000,
        "total_conversions": 450,
        "avg_ctr": 3.0,
        "roas": 3.5,
    }

    # Metrics row
    cols = st.columns(6)
    metrics = [
        ("Total Spend", f"${summary['total_spend']:,.0f}", None),
        ("Impressions", f"{summary['total_impressions']:,.0f}", None),
        ("Clicks", f"{summary['total_clicks']:,.0f}", None),
        ("Conversions", f"{summary['total_conversions']:,.0f}", None),
        ("CTR", f"{summary['avg_ctr']:.2f}%", None),
        ("ROAS", f"{summary['roas']:.2f}x", None),
    ]

    for col, (label, value, delta) in zip(cols, metrics):
        with col:
            st.metric(label, value, delta)

    st.divider()

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Daily Performance")
        # Mock daily data
        dates = pd.date_range(
            st.session_state.date_range[0], st.session_state.date_range[1], freq="D"
        )
        daily_data = pd.DataFrame(
            {
                "Date": dates,
                "Spend": [800 + i * 10 + (i % 7) * 50 for i in range(len(dates))],
                "Conversions": [12 + (i % 5) * 3 for i in range(len(dates))],
            }
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_data["Date"],
                y=daily_data["Spend"],
                name="Spend ($)",
                line=dict(color="#1a365d"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_data["Date"],
                y=daily_data["Conversions"] * 50,
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

    with col2:
        st.markdown("#### Channel Breakdown")
        channel_data = pd.DataFrame(
            {
                "Channel": ["Google Ads", "Meta"],
                "Spend": [15000, 10000],
                "Conversions": [280, 170],
            }
        )

        fig = px.pie(
            channel_data,
            values="Spend",
            names="Channel",
            color_discrete_sequence=["#1a365d", "#4299e1"],
        )
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Campaign table
    st.markdown("#### Campaign Performance")
    campaign_data = pd.DataFrame(
        {
            "Campaign": [
                "Summer Sale - Google Ads",
                "Brand Awareness - Meta",
                "Retargeting - Google Ads",
                "Lead Gen - Meta",
            ],
            "Status": ["Active", "Active", "Paused", "Active"],
            "Spend": [8000, 6000, 5000, 6000],
            "Clicks": [5000, 4000, 3500, 2500],
            "Conversions": [150, 120, 100, 80],
            "CTR": [3.2, 2.8, 3.0, 2.5],
            "ROAS": [4.2, 3.8, 3.5, 2.9],
        }
    )

    st.dataframe(
        campaign_data,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.0f"),
            "CTR": st.column_config.NumberColumn("CTR", format="%.2f%%"),
            "ROAS": st.column_config.NumberColumn("ROAS", format="%.2fx"),
        },
    )


def reports_page():
    """Render reports generation page."""
    st.markdown('<h1 class="main-header">Reports</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_name = st.session_state.selected_client["name"]
    client_id = st.session_state.selected_client["id"]

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
                st.info(
                    "The report is being generated. Refresh the page to check status."
                )
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


def upload_page():
    """Render data upload page."""
    st.markdown('<h1 class="main-header">Data Upload</h1>', unsafe_allow_html=True)

    if not st.session_state.selected_client:
        st.warning("Please select a client from the sidebar")
        return

    client_name = st.session_state.selected_client["name"]
    client_id = st.session_state.selected_client["id"]

    st.markdown(f"### Upload Data for {client_name}")

    st.info(
        """
        Upload CSV files with your marketing data. Supported formats:
        - **Campaigns**: Columns: name, objective, start_date, end_date, budget, channel
        - **Metrics**: Columns: campaign_id, date, impressions, clicks, conversions, spend, revenue, currency
        """
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Upload campaign or metrics data in CSV format",
    )

    if uploaded_file is not None:
        # Preview data
        df = pd.read_csv(uploaded_file)
        st.markdown("#### Preview")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("Upload Data", type="primary"):
            uploaded_file.seek(0)  # Reset file pointer

            response = api_request(
                "POST",
                f"/ingest/csv/{client_id}",
                files={"file": (uploaded_file.name, uploaded_file, "text/csv")},
            )

            if response and response.status_code == 200:
                data = response.json()
                st.success(f"Successfully uploaded {data.get('rows_processed', 0)} rows")
            else:
                st.error("Failed to upload data")

    st.divider()

    # Generate mock data option (for testing)
    if st.session_state.user.get("role") == "admin":
        st.markdown("### Generate Mock Data")
        st.caption("Admin only: Generate sample data for testing")

        col1, col2 = st.columns(2)
        with col1:
            num_campaigns = st.number_input("Number of campaigns", 1, 10, 4)
        with col2:
            num_days = st.number_input("Days of history", 7, 365, 90)

        if st.button("Generate Mock Data"):
            response = api_request(
                "POST",
                f"/ingest/mock/{client_id}?campaigns={num_campaigns}&days={num_days}",
            )

            if response and response.status_code == 200:
                data = response.json()
                st.success(
                    f"Generated {data.get('campaigns', 0)} campaigns "
                    f"with {data.get('metrics', 0)} metric records"
                )
            else:
                st.error("Failed to generate mock data")


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
    elif page == "Data Upload":
        upload_page()


if __name__ == "__main__":
    main()
