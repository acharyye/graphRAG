# Marketing GraphRAG - User Guide

Welcome to Marketing GraphRAG, your AI-powered marketing analytics assistant. This guide will help you understand what the application does and how to use it effectively.

---

## What is Marketing GraphRAG?

Marketing GraphRAG is an intelligent analytics platform that lets you **ask questions about your marketing data in plain English**. Instead of digging through spreadsheets or complex dashboards, simply type your question and get instant, accurate answers with sources.

### Key Benefits

- **No technical skills required** - Ask questions in everyday language
- **Instant insights** - Get answers in seconds, not hours
- **Trustworthy results** - Every answer includes confidence scores and data sources
- **Multi-platform support** - Combines data from Google Ads, Meta (Facebook/Instagram), and more
- **Automated reports** - Generate professional PDF, Excel, or CSV reports with one click

---

## Getting Started

### Step 1: Sign In

1. Open the application in your web browser
2. Enter your email and password
3. Click **Sign In**

**Default test accounts:**
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@agency.com | password123 |
| Analyst | analyst@agency.com | password123 |
| Manager | manager1@agency.com | password123 |

### Step 2: Select a Client

After signing in, use the **sidebar** on the left to:
1. Select the client you want to analyze from the dropdown
2. Choose your desired date range

---

## Main Features

### 1. Ask Questions (Query Page)

This is your main workspace for getting insights from your marketing data.

**How to use:**
1. Navigate to **Query** in the sidebar
2. Type your question in the chat box at the bottom
3. Press Enter or click Send

**Example questions you can ask:**
- "What was our total ad spend last month?"
- "Which campaigns have the highest return on ad spend (ROAS)?"
- "Compare Google Ads vs Meta performance this quarter"
- "Show me campaigns with declining conversion rates"
- "What's the cost per acquisition for our lead generation campaigns?"
- "Which ad creatives performed best?"

**Understanding the response:**
- **Answer** - The AI's response to your question
- **Confidence Level** - How certain the system is (High/Medium/Low)
- **Sources** - The specific data used to generate the answer
- **Recommendations** - Suggested actions based on the analysis

> **Tip:** If you see a LOW confidence score, the system may not have enough data. Try rephrasing your question or selecting a broader date range.

### 2. Dashboard

Get a visual overview of your marketing performance at a glance.

**What you'll see:**
- **Key Metrics** - Total spend, impressions, clicks, conversions, CTR, and ROAS
- **Performance Charts** - Daily trends showing spend and conversions over time
- **Channel Breakdown** - Pie chart showing spend distribution across platforms
- **Campaign Table** - Detailed view of each campaign's performance

### 3. Reports

Generate professional reports to share with your team or clients.

**How to generate a report:**
1. Navigate to **Reports** in the sidebar
2. Choose report type: Monthly, Weekly, Daily, Quarterly, or Custom
3. Select output format: PDF, Excel, or CSV
4. Pick which sections to include:
   - Summary
   - Campaigns
   - Ad Sets
   - Trends
   - Recommendations
   - Channel Breakdown
5. Optionally enable "Compare to previous period"
6. Click **Generate Report**

**Downloading reports:**
- Reports appear in the "Recent Reports" section below
- Click **Download** when status shows "COMPLETED"

### 4. Data Upload

Upload your own marketing data via CSV files.

**Supported file formats:**

**Campaign data columns:**
- name, objective, start_date, end_date, budget, channel

**Metrics data columns:**
- campaign_id, date, impressions, clicks, conversions, spend, revenue, currency

**How to upload:**
1. Navigate to **Data Upload** in the sidebar
2. Click "Choose a CSV file" or drag and drop your file
3. Review the preview to ensure data looks correct
4. Click **Upload Data**

---

## Understanding Key Metrics

| Metric | What It Means |
|--------|---------------|
| **Impressions** | Number of times your ads were shown |
| **Clicks** | Number of times people clicked on your ads |
| **Conversions** | Number of desired actions (purchases, sign-ups, etc.) |
| **Spend** | Total amount spent on advertising |
| **CTR (Click-Through Rate)** | Percentage of impressions that resulted in clicks |
| **ROAS (Return on Ad Spend)** | Revenue generated per dollar spent on ads |
| **CPA (Cost Per Acquisition)** | Average cost to acquire one conversion |

---

## Tips for Best Results

### Asking Better Questions

**Be specific about time periods:**
- Instead of: "How are we doing?"
- Ask: "What was our ROAS for Q4 2024?"

**Mention the metrics you care about:**
- Instead of: "Tell me about our campaigns"
- Ask: "Which campaigns had the highest conversion rates last month?"

**Ask follow-up questions:**
The system remembers your conversation, so you can ask:
1. "What was our top performing campaign?"
2. "Why did it perform so well?"
3. "How does it compare to last quarter?"

### Common Issues

**"Cannot connect to API server"**
- The backend service may not be running. Contact your administrator.

**Low confidence answers**
- Try selecting a broader date range
- Check if data exists for the selected client and time period

**"Please select a client"**
- Use the sidebar dropdown to select which client's data to analyze

---

## Data Security

- Your data is stored securely and isolated by client
- Each user only sees data they're authorized to access
- All queries are logged for compliance and auditing
- No personally identifiable information (PII) is sent to the AI

---

## Need Help?

If you encounter issues or have questions:
1. Check this guide for common solutions
2. Contact your system administrator
3. Report technical issues to your IT team

---

*Marketing GraphRAG - Powered by AI, Driven by Data*
