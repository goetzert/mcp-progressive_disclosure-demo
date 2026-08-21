# MCP Progressive Disclosure Demo

A demo application that showcases **progressive disclosure** in the Model
Context Protocol (MCP). The app runs two MCP modes side-by-side and measures
the token reduction achieved by progressive tool injection.

## How It Works

### Normal Mode

All ~100 tool schemas are sent to the LLM in a single API call. The LLM
selects a tool, the MCP server executes it, and the LLM generates the final
answer.

### Progressive Mode

Only a lightweight `search_tools` schema is sent initially. The LLM calls
`search_tools`, a local keyword search returns the top candidate tools, those
schemas are dynamically injected into the next API call, and the LLM calls
the relevant tool — achieving the same result with dramatically fewer tokens.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure API key
cp .env.example .env
# Edit .env: set SCADSAI_API_KEY

# 3. Start MCP server (terminal 1)
uv run python -m mcp_server.server

# 4. Start backend (terminal 2)
uv run python -m backend.main

# 5. Open browser
# http://localhost:8080
```

## Configuration

All settings are loaded from `.env` via `backend/config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SCADSAI_API_KEY` | — | Required: API key from scads.ai portal |
| `SCADSAI_API_BASE` | `https://llm.scads.ai/v1` | API base URL |
| `SCADSAI_CHAT_MODEL` | `alias-vision` | Chat model (alternatives: `alias-huge`, `alias-code`, `alias-reasoning`) |
| `SCADSAI_REQUEST_TIMEOUT` | `60` | Request timeout in seconds |
| `MCP_SERVER_HOST` | `127.0.0.1` | MCP server bind address |
| `MCP_SERVER_PORT` | `8000` | MCP server port |
| `BACKEND_HOST` | `127.0.0.1` | Backend bind address |
| `BACKEND_PORT` | `8080` | Backend port |

## Architecture

```
Frontend (HTML/CSS/JS)
    │
    │ HTTP POST /api/demo
    ▼
Backend (Starlette)
    ├── naive_mode.py      → all tools sent to LLM
    ├── progressive_mode.py → only search_tools sent, then dynamic injection
    ├── mcp_client.py      → MCP client (list_tools, call_tool)
    ├── llm_client.py      → scadsapi client (httpx)
    ├── token_counter.py   → tiktoken-based counting
    └── tool_search.py     → keyword search over tool definitions
    │
    │ MCP Protocol (HTTP, port 8000)
    ▼
MCP Server (FastMCP)
    └── ~100 tools: weather, customers, orders, finance, dummy
```

## API Endpoints

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

## Tool Inventory (101 total)

| Module | Count | Examples |
|--------|-------|---------|
| `weather.py` | 10 | get_weather, get_forecast, get_humidity, get_uv_index |
| `customers.py` | 12 | search_customers, get_customer, create_customer |
| `orders.py` | 12 | create_order, get_order, cancel_order, ship_order |
| `finance.py` | 12 | get_invoice, create_invoice, calculate_tax |
| `dummy.py` | 55 | analyze_data, backup_database, check_inventory, ... |

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server + client framework |
| `httpx` | scadsapi HTTP calls |
| `tiktoken` | Accurate token counting |
| `starlette` | Backend web framework |
| `uvicorn` | ASGI server |
| `pydantic-settings` | Configuration management |

## License

MIT
