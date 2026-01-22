# Marketing GraphRAG

A Graph-based Retrieval Augmented Generation (RAG) system for marketing agency analytics, built with Neo4j, LlamaIndex, and Claude.

## Features

- **Natural Language Queries**: Ask questions about marketing data in plain English
- **Multi-Platform Support**: Integrates with Google Ads and Meta Marketing APIs
- **GraphRAG Architecture**: Combines knowledge graph with LLM for accurate, sourced answers
- **Confidence Scoring**: Refuses to answer when data is insufficient
- **Multi-Currency Support**: Handles USD, EUR, GBP
- **Report Generation**: PDF, Excel, CSV exports
- **Conversation Memory**: Support for follow-up questions
- **Role-Based Access**: Admin, Analyst, Manager, Executive roles
- **Audit Logging**: Full query logging for compliance
- **Strict Client Isolation**: Multi-tenant data security

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: Neo4j 5.x
- **LLM**: Claude claude-sonnet-4-20250514 (via Anthropic API)
- **Embeddings**: Voyage AI
- **UI**: Streamlit
- **Deployment**: Docker, Azure-ready

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- API keys for Anthropic and Voyage AI

### Setup

1. Clone and install dependencies:

```bash
cd marketing-graphrag
pip install -e ".[dev]"
```

2. Copy environment template and configure:

```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start Neo4j:

```bash
docker-compose up -d neo4j
```

4. Seed mock data (for testing):

```bash
python scripts/seed_mock_data.py
```

5. Run the API:

```bash
uvicorn src.api.main:app --reload
```

6. Run the UI (in a separate terminal):

```bash
streamlit run src/ui/app.py
```

### Default Test Credentials

- **Admin**: admin@agency.com / password123
- **Analyst**: analyst@agency.com / password123
- **Manager**: manager1@agency.com / password123

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get access token
- `POST /api/auth/register` - Register new user (admin only)
- `GET /api/auth/me` - Get current user info

### Queries
- `POST /api/query` - Natural language query
- `POST /api/query/drill-down` - Get detailed breakdown (analysts only)
- `DELETE /api/query/session/{session_id}` - Clear conversation memory

### Data Ingestion
- `GET /api/ingest/clients` - List accessible clients
- `POST /api/ingest/clients` - Create client (admin only)
- `POST /api/ingest/sync/google-ads/{client_id}` - Trigger Google Ads sync
- `POST /api/ingest/sync/meta/{client_id}` - Trigger Meta sync
- `POST /api/ingest/csv/{client_id}` - Upload CSV data
- `POST /api/ingest/mock/{client_id}` - Generate mock data (dev only)

### Reports
- `POST /api/reports` - Generate report
- `GET /api/reports` - List reports
- `GET /api/reports/{report_id}` - Get report status
- `GET /api/reports/{report_id}/download` - Download report

## Project Structure

```
marketing-graphrag/
├── src/
│   ├── connectors/      # Platform API connectors
│   ├── graph/           # Neo4j schema and operations
│   ├── rag/             # GraphRAG engine
│   ├── api/             # FastAPI application
│   ├── services/        # Business logic services
│   └── ui/              # Streamlit UI
├── tests/               # Unit and integration tests
├── config/              # Configuration management
├── scripts/             # Utility scripts
├── docker-compose.yml   # Local development setup
└── pyproject.toml       # Python dependencies
```

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | Yes |
| `VOYAGE_API_KEY` | Voyage AI API key | Yes |
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `GOOGLE_ADS_*` | Google Ads API credentials | No |
| `META_*` | Meta Marketing API credentials | No |
| `SLACK_WEBHOOK_URL` | Slack notifications | No |
| `SENDGRID_API_KEY` | Email notifications | No |

## Development

### Running Tests

```bash
pytest tests/unit -v --cov=src
```

### Code Quality

```bash
ruff check src tests
ruff format src tests
```

## Azure Deployment

The application is designed for Azure deployment:

- **Neo4j**: Azure Marketplace or Neo4j Aura
- **API**: Azure Container Apps
- **UI**: Azure Container Apps
- **Monitoring**: Azure Monitor
- **Secrets**: Azure Key Vault

## GDPR Compliance

- Configurable data retention per client
- No PII in LLM prompts/responses
- Full audit logging
- Right to deletion support
- EU region deployment option

## License

Proprietary - All rights reserved.
