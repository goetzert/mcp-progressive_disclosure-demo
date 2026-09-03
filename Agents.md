# AGENTS.md — Progressive Disclosure Demo for MCP

## Project Overview

A demo application that showcases **progressive disclosure** in the Model
Context Protocol (MCP). The app runs two MCP modes side-by-side:

1. **Normal Mode** — All ~100 tool schemas are sent to the LLM upfront.
2. **Progressive Mode** — Only a lightweight `search_tools` schema is sent
   initially. Relevant tool schemas are injected dynamically after a search
   step.

The web UI displays token counts, tool counts, and a step-by-step flow
visualization for each mode, plus a token-reduction bar chart.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Frontend (HTML/CSS/JS)                     │
│  Side-by-side: Normal MCP vs Progressive MCP         │
│  Token reduction bar chart + prompt input            │
└────────────────────┬────────────────────────────────┘
                     │ HTTP POST /api/demo
┌────────────────────┴────────────────────────────────┐
│           Backend (Starlette/Uvicorn)                │
│  ┌────────────┐  ┌──────────────────┐  ┌─────────┐ │
│  │naive_mode  │  │progressive_mode  │  │token_   │ │
│  │(all tools) │  │(search_tools)    │  │counter  │ │
│  └─────┬──────┘  └────────┬─────────┘  └─────────┘ │
│  ┌─────┴──────────────────┴──────────┐              │
│  │ mcp_client | llm_client | config  │              │
│  └───────────────────────────────────┘              │
└────────────────────┬────────────────────────────────┘
                     │ In-Memory MCP Protocol (FastMCP)
┌────────────────────┴────────────────────────────────┐
│           MCP Server (FastMCP)                       │
│  ~100 tools: weather, customers, orders,            │
│  finance, dummy                                      │
└─────────────────────────────────────────────────────┘
```

The MCP server and backend run in the **same process** using FastMCP's
in-memory transport (`Client(mcp)`). This avoids the need for a separate
MCP server terminal and SSE handling issues on Windows.

### Component Descriptions

**MCP Server (`mcp_server/`)**
- `server.py` — FastMCP server, loads all tool modules, can also run standalone on port 8000
- `tools/weather.py` — 10 weather tools (get_weather, get_forecast, get_humidity, etc.)
- `tools/customers.py` — 12 customer tools (search, get, create, update, delete, etc.)
- `tools/orders.py` — 12 order tools (create, get, list, cancel, etc.)
- `tools/finance.py` — 12 finance tools (get_invoice, create_invoice, calculate_tax, etc.)
- `tools/dummy.py` — 55 programmatically generated dummy tools to reach 101 total

All tools return fixed, hardcoded dummy data (no database or JSON files) —
this is a token-counting demo, not a functional business app.

**Backend (`backend/`)**
- `config.py` — pydantic-settings for SCADSAI_API_KEY, API_BASE, CHAT_MODEL, ports
- `llm_client.py` — scadsapi client using httpx (chat completions with tool calling support)
- `mcp_client.py` — MCP client using FastMCP in-memory transport (list_tools, call_tool)
- `token_counter.py` — tiktoken-based token counting (schema tokens, message tokens, totals)
- `tool_search.py` — keyword-based search over tool definitions with German-English mapping
- `naive_mode.py` — Normal MCP mode (all 101 tool schemas sent to LLM)
- `progressive_mode.py` — Progressive MCP mode (only search_tools sent, dynamic tool injection)
- `main.py` — Starlette app (API endpoints + static frontend serving)

**Frontend (`frontend/`)**
- `index.html` — Side-by-side comparison panels with terminal aesthetic
- `styles.css` — Dark background, monospace font, green/cyan text, box-drawing panels
- `app.js` — API calls, dynamic step-by-step updates, flow visualization, token reduction bars

## Two Modes Comparison

### Normal Mode (naive_mode.py)

```
User: "Wie ist das Wetter in Leipzig?"
      ↓
LLM receives ALL 101 tool schemas (~9,699 schema tokens)
      ↓
LLM calls: get_weather(city="Leipzig")
      ↓
MCP server executes tool → returns weather data
      ↓
LLM generates final answer

Total tokens: ~9,699+ (schema tokens + conversation tokens)
```

### Progressive Mode (progressive_mode.py)

```
User: "Wie ist das Wetter in Leipzig?"
      ↓
LLM receives ONLY search_tools schema (~53 schema tokens)
      ↓
LLM calls: search_tools(query="Wetter Leipzig")
      ↓
tool_search returns 5 candidates: [get_weather, get_forecast, ...]
      ↓
Candidate tool schemas dynamically injected → LLM calls get_weather(city="Leipzig")
      ↓
MCP server executes tool → returns weather data
      ↓
LLM generates final answer

Total tokens: ~53+ (schema tokens + conversation tokens)
Token reduction: ~99.5% (schema tokens only)
```

## Progressive Mode — Detailed Flow

The progressive mode uses **dynamic tool injection** across multiple LLM API calls:

1. **API Call 1 (Search):**
   - Messages: `[system: "Use search_tools to find relevant tools", user: "Wie ist das Wetter in Leipzig?"]`
   - Tools: `[search_tools(query: str) → list[dict]]` (1 tool only)
   - LLM responds: `tool_call(search_tools, {query: "Wetter Leipzig"})`

2. **Execute search_tools locally:**
   - `tool_search.py` searches all 101 tool definitions by keyword
   - German-English keyword mapping ensures cross-language search
   - Returns top-5 candidates with full schemas: `[get_weather, get_forecast, get_temperature, get_weather_alerts, get_humidity]`

3. **API Call 2 (Execute):**
   - Messages: `[system, user, assistant(search_tools call), tool(search results), assistant(get_weather call), tool(weather data)]`
   - Tools: `[get_weather, get_forecast, ...]` (dynamically injected candidate tools)
   - LLM responds: `tool_call(get_weather, {city: "Leipzig"})`

4. **API Call 3 (Answer):**
   - Messages: previous conversation + tool result
   - LLM generates: `"Das aktuelle Wetter in Leipzig ist sonnig bei 21°C."`

**Token counting:**
- "Tools sent to LLM": 1 (only search_tools in initial request)
- "Schema tokens": 53 (search_tools schema only, in initial request)
- Additional candidate schemas injected in call 2 are counted as conversation tokens
- "Total tokens": sum of all schema + conversation tokens across all API calls

## Configuration

`.env` file (loaded by `backend/config.py` via pydantic-settings):

```env
# ScaDS.AI API
SCADSAI_API_KEY=                    # Required: API key from scads.ai portal
SCADSAI_API_BASE=https://llm.scads.ai/v1
SCADSAI_CHAT_MODEL=alias-vision     # Alternatives: alias-huge, alias-code, alias-reasoning
SCADSAI_REQUEST_TIMEOUT=60

# MCP Server
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000

# Backend
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8080
```

## How to Run

```bash
# 1. Setup
cp .env.example .env
# Edit .env: set SCADSAI_API_KEY
uv sync

# 2. Start backend (serves frontend + MCP server in one process)
uv run python -m backend.main

# 3. Open browser: http://localhost:8080
```

Alternatively, the MCP server can be run standalone for testing:

```bash
uv run python -m mcp_server.server
# Server runs at http://127.0.0.1:8000/mcp
```

## Dependencies

Only `tiktoken` is genuinely new. Others are already in the venv as fastmcp dependencies:

| Package | Status | Purpose |
|---------|--------|---------|
| tiktoken | NEW | Accurate token counting |
| httpx | already installed | scadsapi HTTP calls |
| starlette | already installed | Backend web framework |
| uvicorn | already installed | ASGI server |
| pydantic-settings | already installed | Configuration management |
| fastmcp | already installed | MCP server framework |

**Note on tiktoken + Python 3.14:** Compatibility needs to be verified during implementation. If tiktoken doesn't install/work on Python 3.14, we'll fall back to a character-based approximation (~4 chars/token).

## Development Conventions

- Python 3.14, uv-based project management
- FastMCP for both MCP server and client
- Starlette for backend web server (already available via fastmcp deps)
- Plain HTML/CSS/JS for frontend (no build step)
- Tiktoken for precise token counting
- All tool functions return dict or list[dict]
- Tool docstrings are detailed (used for search indexing)
- `.env` for configuration, never commit secrets

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project structure, config, AGENTS.md | ✅ COMPLETE |
| 2 | MCP server with ~100 tools (10 weather + 12 customer + 12 order + 12 finance + 55 dummy = 101) | ✅ COMPLETE |
| 3 | Backend core (token_counter, tool_search, llm_client, mcp_client) | ✅ COMPLETE |
| 4 | Backend modes (naive_mode, progressive_mode) | ✅ COMPLETE |
| 5 | Backend web server (main.py, API endpoints, static files) | ✅ COMPLETE |
| 6 | Frontend (index.html, styles.css, app.js) | ✅ COMPLETE |
| 7 | Documentation (README.md), AGENTS.md final update, end-to-end test | ✅ COMPLETE |

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-19 | Use pydantic-settings for config | Already available, type-safe, .env support |
| 2026-08-19 | Plain HTML/CSS/JS frontend | No build step, fast iteration |
| 2026-08-19 | tiktoken for token counting | Precise, OpenAI-compatible |
| 2026-08-19 | Starlette for backend web server | Already available via fastmcp deps |
| 2026-08-19 | FastMCP for MCP server and client | Project already uses fastmcp |
| 2026-08-19 | ~100 tools total | Enough to show dramatic token difference |
| 2026-08-21 | In-memory transport instead of HTTP | Avoids SSE handling issues on Windows; simpler single-process setup |

## Known Issues

- tiktoken compatibility with Python 3.14 needs verification
- scadsapi tool calling support is uncertain — may need fallback to prompt-based tool calling
- HTTP transport for MCP server has issues with SSE on Windows — in-memory transport used instead

## File Tree

```
mcp_progressive_disclosure/
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── AGENTS.md
├── README.md
├── mcp_server/
│   ├── __init__.py
│   ├── server.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── weather.py
│   │   ├── customers.py
│   │   ├── orders.py
│   │   ├── finance.py
│   │   └── dummy.py
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── mcp_client.py
│   ├── llm_client.py
│   ├── naive_mode.py
│   ├── progressive_mode.py
│   ├── tool_search.py
│   └── token_counter.py
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```