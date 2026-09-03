# MCP Progressive Disclosure Demo

A demo application that showcases **progressive disclosure** in the Model
Context Protocol (MCP). The app runs two MCP modes side-by-side and measures
the token reduction achieved by progressive tool injection.

> Setup & Ausführung: siehe [SETUP.md](SETUP.md)

## What is Progressive Disclosure?

Normalerweise bekommt eine LLM alle verfügbaren Tools auf einmal gezeigt —
bei 101 Tools sind das tausende Tokens an Schema-Definitionen, bei jeder
einzelnen Anfrage, egal ob sie gebraucht werden oder nicht. Progressive
Disclosure dreht das um: die LLM sieht zunächst nur eine einzige
Suchfunktion (`search_tools`). Erst wenn sie damit passende Tools gefunden
hat, werden genau deren Schemas nachgeladen. Das Ergebnis: die LLM bekommt
weiterhin Zugriff auf alle 101 Tools, aber der Großteil der Schema-Tokens
fällt weg.

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
    │ In-Memory MCP Protocol (FastMCP)
    ▼
MCP Server (FastMCP)
    └── ~100 tools: weather, customers, orders, finance, dummy
```

## Tool Inventory (101 total)

| Module | Count | Examples |
|--------|-------|---------|
| `weather.py` | 10 | get_weather, get_forecast, get_humidity, get_uv_index |
| `customers.py` | 12 | search_customers, get_customer, create_customer |
| `orders.py` | 12 | create_order, get_order, cancel_order, ship_order |
| `finance.py` | 12 | get_invoice, create_invoice, calculate_tax |
| `dummy.py` | 55 | analyze_data, backup_database, check_inventory, ... |

## License

MIT
