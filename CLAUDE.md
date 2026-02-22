# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

n8n workflow search engine — indexes 2,000+ n8n workflow JSON exports and serves them via a FastAPI web UI with full-text search. Sub-100ms response times, ~50MB memory. Forked from [Zie619/n8n-workflows](https://github.com/Zie619/n8n-workflows).

## Commands

```bash
# Run locally (uses Python 3.12 venv — Python 3.14 cannot build pydantic-core)
.venv/bin/python run.py                    # Start server (127.0.0.1:8000)
.venv/bin/python run.py --dev              # Dev mode with auto-reload
.venv/bin/python run.py --host 0.0.0.0     # Accept external connections
.venv/bin/python run.py --port 3000        # Custom port
.venv/bin/python run.py --reindex          # Force database reindex
.venv/bin/python run.py --skip-index       # Skip indexing (CI mode)

# Docker
docker compose up -d                       # Production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d  # Dev (hot-reload)

# Tests
python test_workflows.py                   # Validate workflow JSON structure
bash test_api.sh                           # API endpoint tests
bash test_security.sh                      # Security tests

# AI Stack (separate Docker Compose in ai-stack/)
cd ai-stack && ./start.sh                  # n8n + Agent Zero + ComfyUI
```

## Architecture

### Core: Three-File Server

```
run.py          → Entry point: dependency check, directory setup, DB init, uvicorn launch
api_server.py   → FastAPI app: 7 API endpoints, rate limiting, CORS, security middleware
workflow_db.py  → WorkflowDatabase class: SQLite FTS5 indexing, search, metadata extraction
```

### Request Flow

Browser → `static/index.html` → FastAPI (`api_server.py`) → `WorkflowDatabase` (`workflow_db.py`) → SQLite (`database/workflows.db`)

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Serve web UI |
| `GET /api/workflows` | Search with FTS5 (params: `q`, `trigger`, `complexity`, `active_only`, `page`, `per_page`) |
| `GET /api/stats` | Database statistics |
| `GET /api/categories` | List all categories |
| `GET /api/workflow/{id}` | Get workflow JSON |
| `GET /api/export` | Export workflows |
| `POST /api/reindex` | Reindex database (requires `admin_token` param) |
| `GET /health` | Health check |

### WorkflowDatabase (`workflow_db.py`)

The core of the system. Key details:

- **Schema:** `workflows` table with filename, name, trigger_type, complexity (low/medium/high), node_count, integrations (JSON), tags (JSON), file_hash (MD5 for change detection)
- **FTS5 virtual table:** full-text search on filename, name, description, integrations, tags
- **`analyze_workflow_file()`** — parses workflow JSON, extracts metadata, detects trigger types and integrations from node types
- **`index_all_workflows()`** — scans `workflows/` directory, indexes new/changed files (MD5 hash comparison), skips unchanged
- **100+ integration mappings** — maps n8n node types to service names (e.g., `n8n-nodes-base.telegram` → `Telegram`)
- **WAL mode** enabled for concurrent read performance

### Security (`api_server.py`)

- **Rate limiting:** 60 req/min per IP (in-memory, `rate_limit_storage` defaultdict)
- **Path traversal prevention:** `validate_filename()` blocks `..`, URL-encoded variants, shell chars; regex whitelist `^[a-zA-Z0-9_\-]+\.json$`
- **CORS:** restricted to specific origins (localhost + GitHub Pages + Render deployment)
- **Reindex protection:** requires `ADMIN_TOKEN` env var

### Optional Modules (`src/`)

Extended features not loaded by default — these are independent modules:

| Module | Purpose |
|--------|---------|
| `ai_assistant.py` | NLP intent detection, intelligent keyword extraction for search |
| `user_management.py` | JWT auth, bcrypt password hashing, role-based access |
| `performance_monitor.py` | WebSocket dashboard, CPU/memory/disk metrics, alerts |
| `analytics_engine.py` | Workflow trends, patterns, category distribution |
| `community_features.py` | Ratings (1-5), reviews, helpful votes |
| `enhanced_api.py` | Advanced search, recommendations, aggregation |
| `integration_hub.py` | Webhook management, GitHub sync, API connectors |

Legacy Node.js files (`src/database.js`, `src/server.js`, etc.) are from the original upstream — the Python stack has replaced them.

## Environment Variables

See `.env.example`. Key variables:

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET_KEY` | JWT signing key |
| `ADMIN_PASSWORD` | Admin user password |
| `ADMIN_TOKEN` | Token for `/api/reindex` endpoint |
| `WORKFLOW_DB_PATH` | SQLite path (default: `database/workflows.db`) |
| `HOST` | Bind address (default: `127.0.0.1`) |
| `PORT` | Server port (default: `8000`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

## Deployment

- **Docker:** Multi-stage Dockerfile (Python 3.12-slim): builder → development → production. Uses `/opt/venv` virtual environment pattern for non-root user (`appuser`, UID 1001) compatibility. Production stage runs with `--skip-index` (uses pre-built DB). Health check on `/health`. Also available via top-level `docker-compose.yml` as `n8n-workflows` service (host port 8000).
- **Kubernetes:** Manifests in `k8s/` — 2 replicas, resource limits (512Mi/500m), persistent volumes for DB and logs.
- **Helm:** Chart in `helm/workflows-docs/`.
- **Direct:** `pip install -r requirements.txt && python run.py`

## Parallel Projects

- **`ai-stack/`** — Docker Compose stack: n8n (5678) + Agent Zero (50080) + ComfyUI (8188, needs NVIDIA GPU). Launch: `./start.sh`
- **`medcards-ai/`** — Next.js 14 medical exam prep app (Supabase + Claude). Separate project, not related to workflow search.
