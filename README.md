# DevOps Logs Project

AI-powered DevOps log analysis MVP built with FastAPI, async SQLAlchemy, and an Ollama-compatible LLM. It ingests logs from Jenkins, Kubernetes, Terraform, and ArgoCD, runs pluggable detectors, correlates events, and asks an LLM for a plain-English root cause and fix.

## Features
- REST ingestion of JSON logs (`POST /logs`).
- Plugin system with detectors for Jenkins failures, Terraform errors, and Kubernetes CrashLoopBackOff.
- Correlation engine that spots Jenkins -> Terraform -> Kubernetes failure chains.
- AI root-cause analysis via Ollama-compatible endpoint (`/api/generate`).
- Findings stored in PostgreSQL (SQLite fallback for local quick start).
- Minimal, modular folder layout ready for extension.

## Project Structure
```
app/
  main.py            # FastAPI entrypoint
  api/routes.py      # HTTP routes
  core/              # config, plugin manager, sample logs
  db/                # SQLAlchemy base, session, init
  models/            # Pydantic schemas + ORM models
  plugins/           # Base plugin + Jenkins/Terraform/K8s detectors
  services/          # ingestion buffer, correlation, AI client
requirements.txt
```

## Quickstart (local)
1) **Python env**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) **Database**
- Recommended: PostgreSQL (async):
```bash
export DATABASE_URL="postgresql+asyncpg://devops:devops@localhost:5432/devops_logs"
# Ensure the database exists: createdb devops_logs
```
- Fallback for local tests (already default):
```bash
export DATABASE_URL="sqlite+aiosqlite:///./devops_logs.db"
```

3) **Ollama / LLM**
```bash
# Install and start Ollama if not running
ollama serve
# Pull a model; defaults to llama3 in settings
ollama pull llama3
```
The app calls `http://localhost:11434/api/generate` with model `llama3`. Override with `OLLAMA_URL` / `OLLAMA_MODEL` env vars if needed.

4) **Run API**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
FastAPI docs: http://localhost:8000/docs

## Using the APIs
### Ingest sample logs
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d @app/core/sample_logs.json
```

### Trigger analysis (uses buffered logs if none provided)
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
```
Response includes plugin findings, correlation finding (if detected), and AI `analysis` block with `root_cause`, `impact`, and `fix`.

### List findings
```bash
curl http://localhost:8000/findings
```

### Health
```bash
curl http://localhost:8000/health
```

## Extending
- Add plugins by subclassing `app.plugins.base.BasePlugin` and registering in `app/core/plugin_manager.py`.
- Queue/stream ingestion: wire `global_log_buffer.ingest` to Redis or Kafka; the service is kept small to swap storage layers.
- Adjust buffer size/retention and endpoints via environment variables in `app/core/config.py`.

## Notes
- Logs are buffered in-memory for fast correlation; findings and AI summaries persist to the database.
- ArgoCD is accepted as a source; add a plugin for deeper checks if desired.
- Startup auto-creates tables via `app/db/init_db.py`.
