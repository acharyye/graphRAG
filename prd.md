# Marketing Agency GraphRAG - Product Requirements Document

## Overview

A Graph-based Retrieval Augmented Generation (GraphRAG) system for a marketing agency to analyze client and campaign data, generate reports, and surface insights through natural language queries.

## Goals

- Enable natural language querying of client and campaign data
- Generate automated reports and performance analysis
- Surface relationships and patterns across campaigns and clients
- Provide a user-friendly web interface for the team

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Graph Database | Neo4j (Community Edition) |
| RAG Framework | LlamaIndex with Knowledge Graph |
| LLM | Anthropic Claude (claude-sonnet-4-20250514) |
| Embeddings | Voyage AI or OpenAI ada-002 |
| Web Framework | FastAPI + React (or Streamlit for MVP) |
| Data Integrations | Google Ads API, Meta Marketing API, HubSpot API |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI (React/Streamlit)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Query API   │  │ Ingest API  │  │ Report Generation   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GraphRAG Engine                          │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ LlamaIndex KG   │  │ Claude LLM      │                   │
│  │ Query Engine    │  │ Integration     │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Neo4j Graph DB                         │
│  Nodes: Client, Campaign, Ad, Channel, Metric, Report       │
│  Relationships: RUNS, CONTAINS, PERFORMS_ON, GENERATES      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Connectors                          │
│  ┌────────────┐  ┌─────────────┐  ┌───────────────┐         │
│  │ Google Ads │  │ Meta/FB Ads │  │ HubSpot CRM   │         │
│  └────────────┘  └─────────────┘  └───────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Graph Schema

### Nodes

| Node Type | Properties |
|-----------|------------|
| **Client** | id, name, industry, contract_start, budget, status |
| **Campaign** | id, name, objective, start_date, end_date, budget, status |
| **AdSet** | id, name, targeting, budget, bid_strategy |
| **Ad** | id, name, creative_type, copy, cta, asset_url |
| **Channel** | id, name (Google, Meta, LinkedIn, etc.) |
| **Metric** | id, date, impressions, clicks, conversions, spend, revenue |

### Relationships

```
(Client)-[:RUNS]->(Campaign)
(Campaign)-[:ADVERTISES_ON]->(Channel)
(Campaign)-[:CONTAINS]->(AdSet)
(AdSet)-[:CONTAINS]->(Ad)
(Campaign)-[:HAS_METRIC]->(Metric)
(AdSet)-[:HAS_METRIC]->(Metric)
```

## Core Features

### Phase 1: Foundation (MVP)

1. **Data Ingestion Pipeline**
   - Google Ads API connector
   - Meta Marketing API connector
   - Manual CSV upload fallback
   - Scheduled sync (daily)

2. **Graph Construction**
   - Auto-populate Neo4j from API data
   - Entity extraction and relationship mapping
   - Incremental updates

3. **Query Interface**
   - Natural language query input
   - Claude-powered query understanding
   - Graph traversal + vector retrieval hybrid

4. **Basic Web UI**
   - Streamlit-based MVP interface
   - Query input with response display
   - Basic data visualization

### Phase 2: Enhanced Analytics

1. **Report Generation**
   - Weekly/monthly performance reports
   - Client-specific report templates
   - Export to PDF/Google Docs

2. **Comparative Analysis**
   - Cross-campaign performance comparison
   - Channel effectiveness analysis
   - Budget optimization suggestions

3. **Alerting**
   - Performance threshold alerts
   - Anomaly detection
   - Slack/email notifications

### Phase 3: Advanced Features

1. **Predictive Insights**
   - Campaign performance forecasting
   - Budget allocation recommendations

2. **Full Web Application**
   - React frontend with dashboard
   - User authentication
   - Role-based access control

## Project Structure

```
marketing-graphrag/
├── src/
│   ├── connectors/           # API integrations
│   │   ├── google_ads.py
│   │   ├── meta_ads.py
│   │   └── hubspot.py
│   ├── graph/                # Graph operations
│   │   ├── schema.py
│   │   ├── ingest.py
│   │   └── queries.py
│   ├── rag/                  # RAG engine
│   │   ├── engine.py
│   │   ├── prompts.py
│   │   └── retrieval.py
│   ├── api/                  # FastAPI backend
│   │   ├── main.py
│   │   ├── routes/
│   │   └── models/
│   └── ui/                   # Streamlit UI
│       └── app.py
├── tests/
├── config/
│   └── settings.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Implementation Plan

### Step 1: Environment Setup
- [ ] Initialize Python project with Poetry/uv
- [ ] Set up Neo4j (Docker)
- [ ] Configure environment variables
- [ ] Install dependencies (llama-index, neo4j, anthropic, fastapi)

### Step 2: Graph Schema & Database
- [ ] Define Neo4j schema and constraints
- [ ] Create graph utility functions
- [ ] Write sample data seeding script

### Step 3: Data Connectors
- [ ] Implement Google Ads API connector
- [ ] Implement Meta Marketing API connector
- [ ] Create data transformation layer
- [ ] Build ingestion pipeline

### Step 4: GraphRAG Engine
- [ ] Set up LlamaIndex with Neo4j graph store
- [ ] Configure Claude as LLM
- [ ] Implement hybrid retrieval (graph + vector)
- [ ] Create query processing pipeline

### Step 5: API Layer
- [ ] Build FastAPI application
- [ ] Create query endpoint
- [ ] Create data ingestion endpoints
- [ ] Add report generation endpoint

### Step 6: Web UI
- [ ] Build Streamlit interface
- [ ] Add query input and response display
- [ ] Add basic visualizations
- [ ] Add data upload functionality

### Step 7: Testing & Deployment
- [ ] Write unit and integration tests
- [ ] Create Docker Compose setup
- [ ] Document deployment process

## Example Queries

The system should handle queries like:

- "What was the total spend across all clients last month?"
- "Which campaigns had the highest ROAS for Client X?"
- "Compare Meta vs Google Ads performance for Q4"
- "Generate a monthly report for Client Y"
- "Which ad creatives performed best for lead generation campaigns?"
- "Show me clients with declining conversion rates"

## Verification Plan

1. **Unit Tests**: Test each connector, graph operation, and RAG component
2. **Integration Tests**: Test end-to-end query flow
3. **Manual Testing**:
   - Ingest sample campaign data
   - Run example queries and verify accuracy
   - Generate a sample report
4. **Performance**: Query response time < 5 seconds for typical queries

## Dependencies

```
llama-index>=0.10.0
llama-index-graph-stores-neo4j
llama-index-llms-anthropic
neo4j>=5.0.0
anthropic>=0.18.0
fastapi>=0.109.0
uvicorn>=0.27.0
streamlit>=1.31.0
google-ads>=23.0.0
facebook-business>=19.0.0
pandas>=2.0.0
python-dotenv>=1.0.0
```

## Notes

- Start with Streamlit for rapid MVP, migrate to React later if needed
- Use Neo4j Community Edition (free) for small scale
- Consider adding HubSpot integration in Phase 2 for CRM data
- Claude claude-sonnet-4-20250514 recommended for cost/performance balance; upgrade to Opus for complex analysis
