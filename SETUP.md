# Setup & Ausführung

Technische Anleitung zum Starten der Demo. Was die Demo inhaltlich zeigt,
steht in [README.md](README.md).

## Requirements

- **Python 3.14+** (siehe `pyproject.toml`)
- **uv** — falls noch nicht installiert:
  https://docs.astral.sh/uv/getting-started/installation/

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure API key
cp .env.example .env
# Edit .env: set SCADSAI_API_KEY

# 3. Start backend (serves frontend + MCP server in one process)
uv run python -m backend.main

# 4. Open browser
# http://localhost:8080
```

Alternativ kann der MCP-Server auch standalone zum Testen laufen:

```bash
uv run python -m mcp_server.server
# Server runs at http://127.0.0.1:8000/mcp
```

## Configuration

Alle Einstellungen werden aus `.env` geladen (via `backend/config.py`):

| Variable | Default | Description |
|----------|---------|--------------|
| `SCADSAI_API_KEY` | — | Required: API key from scads.ai portal |
| `SCADSAI_API_BASE` | `https://llm.scads.ai/v1` | API base URL |
| `SCADSAI_CHAT_MODEL` | `alias-vision` | Chat model (alternatives: `alias-huge`, `alias-code`, `alias-reasoning`) |
| `SCADSAI_REQUEST_TIMEOUT` | `60` | Request timeout in seconds |
| `MCP_SERVER_HOST` | `127.0.0.1` | MCP server bind address |
| `MCP_SERVER_PORT` | `8000` | MCP server port |
| `BACKEND_HOST` | `127.0.0.1` | Backend bind address |
| `BACKEND_PORT` | `8080` | Backend port |

## API Endpoints (For Developers)

### `POST /api/demo`

Runs both modes and returns results.

**Request:**
```json
{ "message": "Wie ist das Wetter in Leipzig?" }
```

**Response:**
```json
{
  "naive": {
    "mode": "normal",
    "tools_available": 101,
    "tools_sent_to_llm": 101,
    "schema_tokens": 42812,
    "total_tokens": 45201,
    "answer": "...",
    "steps": [...]
  },
  "progressive": {
    "mode": "progressive",
    "tools_available": 101,
    "tools_sent_to_llm": 1,
    "schema_tokens": 218,
    "total_tokens": 1974,
    "answer": "...",
    "steps": [...]
  }
}
```

## Troubleshooting

**Port already in use**
`BACKEND_PORT` (default `8080`) oder `MCP_SERVER_PORT` (default `8000`)
belegt? In `.env` einen anderen Port eintragen und Backend neu starten.

**tiktoken lässt sich nicht installieren**
`backend/token_counter.py` fällt automatisch auf eine Zeichen-Approximation
(~4 Zeichen/Token) zurück, falls `tiktoken` nicht importierbar ist. Die Demo
funktioniert dann weiter, die Token-Zahlen sind nur etwas ungenauer.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server + client framework |
| `httpx` | scadsapi HTTP calls |
| `tiktoken` | Accurate token counting |
| `starlette` | Backend web framework |
| `uvicorn` | ASGI server |
| `pydantic-settings` | Configuration management |
