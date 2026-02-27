# ServiceNow & Moveworks MCP Servers

Two AI-ready servers that let Claude (or any MCP-compatible AI) talk to **ServiceNow** and intelligently search **Moveworks documentation** — all through natural language.

---

## What is this?

**MCP (Model Context Protocol)** is a standard way for AI assistants to call external tools. This project ships two such servers:

| Server | What it does |
|---|---|
| **ServiceNow MCP** | Read/write your ServiceNow instance — knowledge bases, articles, tables, records |
| **Moveworks MCP** | Crawl, index, and search any documentation site (optimised for Moveworks Help) |

Once connected to Claude, you talk naturally:
> *"Create a knowledge base called IT Support and add an article about VPN setup"*
> *"Search the Moveworks docs for how compound actions work"*

---

## Quick Setup

### 1. Install

```bash
git clone https://github.com/KarthikeyanM3011/sn_mcp.git
cd sn_mcp/sn_mcp

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e .
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your ServiceNow details:

```bash
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic        # basic | oauth | api_key
```

The Moveworks server requires no credentials (it crawls public docs).

### 3. Connect to Claude Desktop

Open your Claude Desktop config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add both servers:

```json
{
  "mcpServers": {
    "ServiceNow": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "servicenow_mcp.cli"],
      "env": {
        "SERVICENOW_INSTANCE_URL": "https://your-instance.service-now.com",
        "SERVICENOW_USERNAME": "your-username",
        "SERVICENOW_PASSWORD": "your-password",
        "SERVICENOW_AUTH_TYPE": "basic"
      }
    },
    "Moveworks": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "moveworks_mcp.cli"]
    }
  }
}
```

> Find your Python path: run `which python` (macOS/Linux) or `where python` (Windows) while the virtual environment is active.

Restart Claude Desktop — the tools will appear automatically.

---

## What can it do?

### ServiceNow (13 tools)

**Knowledge base management**

Everything you need to author and publish knowledge content — without logging into the ServiceNow UI:

| Tool | What it does |
|---|---|
| `create_knowledge_base` | Create a new KB for a team or topic |
| `list_knowledge_bases` | See all existing KBs in your instance |
| `create_category` | Add a category to organise articles |
| `list_categories` | Browse category structure |
| `create_article` | Write a new knowledge article |
| `update_article` | Edit an existing article |
| `publish_article` | Make an article visible to users |
| `list_articles` | Search and filter articles across KBs |
| `get_article` | Fetch the full content of a specific article |

**Table access**

Generic read access to any ServiceNow table — useful for pulling incident data, user records, CMDB entries, or any other structured data:

| Tool | What it does |
|---|---|
| `list_tables` | Discover all available tables |
| `get_table` | Inspect a table's columns and schema |
| `list_records` | Query records with filters (e.g. priority, state, date) |
| `get_record` | Fetch a single record by its ID |

**Restrict tools by role** — set `MCP_TOOL_PACKAGE` in the config env to control which tools are exposed to Claude:

| Value | Tools available |
|---|---|
| `full` | All 13 (default) |
| `knowledge_author` | KB tools only |
| `table_explorer` | Table tools only |

This is useful when you want to give different teams access to only what they need.

---

### Moveworks KB (5 tools)

The Moveworks server lets you build a **local, searchable knowledge base** from any documentation website. You point it at URLs or a whole domain — it crawls the pages, stores them locally, and makes them instantly searchable. No re-crawling on every question.

| Tool | What it does |
|---|---|
| `mw_kb_index_pages` | Crawl and index specific URLs you provide |
| `mw_kb_index_domain` | Crawl and index an entire site via its sitemap |
| `mw_kb_list` | Show all indexed pages grouped by domain |
| `mw_kb_search` | Search with hybrid semantic + keyword matching |
| `mw_kb_remove` | Remove specific pages or a whole domain from the index |

**How search works**

Every search runs two passes at the same time:
- **Semantic search** — understands the *meaning* of your query using an AI embedding model, so "how do I trigger an action automatically" can match docs about "event-driven workflows" even without exact word overlap
- **Keyword search (BM25)** — traditional word matching for precision

Results from both are merged and ranked — 70% weight on meaning, 30% on keywords. This gives you the best of both: broad understanding and keyword precision.

**Duplicate prevention**

Before indexing any page, the server checks if it's already stored and skips it automatically. To force a refresh of existing content, pass `force_refresh: true` when calling an index tool.

---

## Example prompts

```
"Index the Moveworks help docs from https://help.moveworks.com/docs/compound-actions"

"Search the knowledge base for how to use script actions"

"List all indexed pages"

"Create a category called 'Network' in my IT Support knowledge base"

"List all incidents with priority 1 from the last 7 days"
```

---

## Authentication options (ServiceNow)

| Type | Required env vars |
|---|---|
| Basic (default) | `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` |
| OAuth | `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET`, `SERVICENOW_TOKEN_URL` |
| API Key | `SERVICENOW_API_KEY` |

---

## Troubleshooting

**Tools don't appear in Claude**
- Restart Claude Desktop after any config change
- Check the Python path is absolute and correct
- Validate the JSON syntax in the config file
- Logs: `~/Library/Logs/Claude/` (macOS) · `%APPDATA%\Claude\logs\` (Windows)

**ServiceNow auth errors**
- Confirm `SERVICENOW_AUTH_TYPE` matches the credentials you provided
- Ensure your ServiceNow user has REST API access enabled

**Moveworks search returns nothing**
- Run `mw_kb_list` to confirm pages are indexed
- Try indexing the page first with `mw_kb_index_pages`

**Enable debug logging**
```bash
SERVICENOW_DEBUG=true
MOVEWORKS_DEBUG=true
```

---

## Tech stack

- **Python 3.11+**, MCP 1.3.0
- **ServiceNow:** REST API via `requests` / `httpx`
- **Moveworks crawler:** `aiohttp` + `beautifulsoup4`
- **Vector store:** ChromaDB (local, persistent)
- **Embeddings:** `sentence-transformers` — `all-MiniLM-L6-v2`
- **Keyword search:** `rank-bm25`
- **Transport:** stdio (Claude Desktop) or SSE HTTP (`moveworks-mcp-sse`, `servicenow-mcp-sse`)

---

Built on the [Model Context Protocol](https://github.com/modelcontextprotocol) by Anthropic.
