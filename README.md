# Backend

The backend uses typed FastAPI routes, an asynchronous HTTPX Ollama client,
environment-based configuration, and optional in-memory session history.

Run from this directory with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

The separate [React frontend](frontend/README.md) provides a browser workspace for chat, research runs, indexed PDFs, and MCP tools.

## Phase 2 hybrid agent

The existing `POST /api/v1/chat` endpoint now routes each request through the
local Qwen model plus optional external tools. Current-information phrases use
the configured Tavily Search API, URLs are extracted with BeautifulSoup, and
configured MCP stdio servers are discovered dynamically and invoked when their
tool name is present in the request. The response includes `sources` and
`tools_used` without changing the existing response fields.

Copy `.env.example` to `.env`, set `SEARCH_API_KEY`, and optionally configure
`MCP_SERVERS_JSON` as a JSON array of servers with `name`, `transport`,
`command`, `args`, `url`, and optional `env` or `headers`. The default
configuration connects to the bundled `local_utility_server` over stdio using
the official MCP Python SDK. Streamable HTTP servers are also supported.

Examples:

```text
POST /api/v1/chat {"message":"What is the latest news about ...?"}
POST /api/v1/chat {"message":"Summarize https://example.com/article"}
```

If no search key or MCP servers are configured, those capabilities are skipped
and local-only requests continue to work through Ollama.

MCP management endpoints are available at `/api/v1/mcp/servers`,
`/api/v1/mcp/tools`, `/api/v1/mcp/refresh`, and
`/api/v1/mcp/execute/{server_name}/{tool_name}`. The bundled server exposes
`calculator`, `current_time`, and `text_length`; tools are discovered through
`tools/list` and executed through `tools/call`, not hardcoded in the agent.

## Phase 4 research agent

The bounded research workflow is available through:

```text
POST /api/agent/research
GET  /api/agent/status/{execution_id}
GET  /api/agent/plan/{execution_id}
GET  /api/agent/evidence/{execution_id}
GET  /api/agent/result/{execution_id}
```

Submit `{"query":"..."}` to start a background execution. The planner selects
local reasoning, Tavily, webpage extraction, RAG, and MCP tasks as needed.
Every execution has an explicit state, bounded step count, task dependencies,
and deduplicated evidence records containing source and task references.
Execution state is in memory for the current backend process; indexed documents
and Chroma vectors remain persistent through the Phase 3 storage layer.
