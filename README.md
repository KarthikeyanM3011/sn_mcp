# ServiceNow & Moveworks MCP Servers

**Dual-server MCP implementation combining ServiceNow API integration with intelligent Moveworks documentation search**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP 1.3.0](https://img.shields.io/badge/MCP-1.3.0-green.svg)](https://github.com/modelcontextprotocol)

## Overview

This repository provides two complementary Model Context Protocol (MCP) servers that work together to enable AI assistants like Claude to interact with ServiceNow instances and intelligently search Moveworks documentation:

- **ServiceNow MCP Server** - Direct integration with ServiceNow APIs for knowledge base management and table operations
- **Moveworks MCP Server** - Advanced documentation search with semantic understanding, intelligent crawling, and persistent knowledge bases

### What Makes This Special?

Unlike standard MCP implementations, this project includes:

✨ **Hybrid Search Engine** - Combines multi-query expansion, semantic embeddings, and keyword matching for superior documentation discovery

🧠 **Semantic Understanding** - Uses sentence-transformers (all-MiniLM-L6-v2) to understand meaning, not just keywords

💾 **Persistent Knowledge Bases** - One-time indexing with instant retrieval, eliminating redundant web crawling

🎯 **Smart Documentation Crawler** - Sitemap-aware crawler with relevance scoring and metadata extraction

🔧 **Tool Package System** - Role-based tool filtering for focused, token-efficient interactions

🌐 **URL Indexing** - Index external documentation with rich metadata (categories, tags, priority)

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [ServiceNow MCP Server](#servicenow-mcp-server)
- [Moveworks MCP Server](#moveworks-mcp-server)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Deployment Options](#deployment-options)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- ServiceNow instance with API access (for ServiceNow MCP)
- 5-10 minutes for setup

### Installation

```bash
# Clone the repository
git clone https://github.com/KarthikeyanM3011/sn_mcp.git
cd sn_mcp/sn_mcp

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

### Configuration

Create a `.env` file with your ServiceNow credentials:

```bash
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic
```

### Test the Servers

```bash
# Test ServiceNow MCP server
servicenow-mcp

# Test Moveworks MCP server (in a new terminal)
moveworks-mcp
```

If you see no errors, you're all set! 🎉

---

## Architecture

This project implements a **dual-server architecture** providing complementary capabilities:

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude AI Assistant                     │
└──────────────┬─────────────────────────┬────────────────────┘
               │                         │
               │ MCP Protocol            │ MCP Protocol
               │                         │
    ┌──────────▼──────────┐   ┌─────────▼──────────┐
    │  ServiceNow MCP     │   │  Moveworks MCP     │
    │  Server             │   │  Server            │
    ├─────────────────────┤   ├────────────────────┤
    │ • KB Management     │   │ • Hybrid Search    │
    │ • Table Operations  │   │ • Semantic Search  │
    │ • Tool Packages     │   │ • URL Indexing     │
    │ • Multi-auth        │   │ • KB Persistence   │
    └──────────┬──────────┘   └─────────┬──────────┘
               │                        │
               │ REST API               │ Web Crawling
               │                        │
    ┌──────────▼──────────┐   ┌─────────▼──────────┐
    │  ServiceNow         │   │  Moveworks Docs    │
    │  Instance           │   │  & External URLs   │
    └─────────────────────┘   └────────────────────┘
```

### Communication Modes

Both servers support two transport modes:

1. **stdio (Standard I/O)** - Direct integration with Claude Desktop
2. **SSE (Server-Sent Events)** - HTTP-based for web applications and custom integrations

---

## ServiceNow MCP Server

### Capabilities

#### Knowledge Base Management (9 tools)

Comprehensive knowledge base operations:

- `create_knowledge_base` - Create new knowledge bases
- `list_knowledge_bases` - List all available knowledge bases
- `create_category` - Organize content with categories
- `list_categories` - Browse category hierarchy
- `create_article` - Author new knowledge articles
- `update_article` - Modify existing articles
- `publish_article` - Make articles visible to users
- `list_articles` - Search and filter articles
- `get_article` - Retrieve full article content

#### Table Operations (4 tools)

Generic ServiceNow table access:

- `list_tables` - Discover available tables
- `get_table` - Inspect table schema and columns
- `list_records` - Query records from any table with filtering
- `get_record` - Fetch specific records by sys_id

### Tool Packages

Control which tools are available based on user roles:

| Package | Description | Tools Included |
|---------|-------------|----------------|
| `full` | All tools (default) | 13 tools |
| `knowledge_author` | KB management only | 9 KB tools |
| `table_explorer` | Table operations only | 4 table tools |
| `none` | No tools (testing) | 0 tools |

**Set via environment variable:**
```bash
export MCP_TOOL_PACKAGE=knowledge_author
```

Or add to `.env`:
```bash
MCP_TOOL_PACKAGE=knowledge_author
```

### Authentication Methods

The ServiceNow server supports three authentication methods:

#### 1. Basic Authentication (Recommended for Getting Started)

```bash
SERVICENOW_AUTH_TYPE=basic
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

#### 2. OAuth Authentication

```bash
SERVICENOW_AUTH_TYPE=oauth
SERVICENOW_CLIENT_ID=your-client-id
SERVICENOW_CLIENT_SECRET=your-client-secret
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_TOKEN_URL=https://your-instance.service-now.com/oauth_token.do
```

#### 3. API Key Authentication

```bash
SERVICENOW_AUTH_TYPE=api_key
SERVICENOW_API_KEY=your-api-key
```

---

## Moveworks MCP Server

### Capabilities

The Moveworks MCP server provides **intelligent documentation search** with advanced AI capabilities.

#### Documentation Query Tools (7 tools)

1. **`query_moveworks_docs`** - Real-time documentation crawler
   - Crawls documentation on-demand
   - Always returns fresh content
   - Slower but comprehensive
   - Best for one-off queries

2. **`index_documentation`** - Build persistent knowledge base
   - One-time indexing operation
   - Creates searchable KB with embeddings
   - Stores at `~/.moveworks_mcp/knowledge_base/`
   - Enables instant searches

3. **`search_knowledge_base`** - Hybrid search engine
   - **Multi-query expansion** - Extracts topics and compound terms
   - **Semantic search** - Understands meaning using ML embeddings
   - **Keyword matching** - Traditional text search
   - Lightning-fast with pre-indexed content

4. **`list_knowledge_bases`** - View all indexed KBs

5. **`delete_knowledge_base`** - Remove cached KBs

6. **`list_kb_documents`** - Browse documents in a KB

7. **`get_document_by_url`** - Retrieve specific documentation pages

#### URL Indexing Tools (5 tools)

Index external documentation and resources:

8. **`index_url`** - Index single URL with metadata
   - Add category, tags, priority
   - Extract and store content
   - Generate semantic embeddings

9. **`index_multiple_urls`** - Batch URL indexing
   - Index multiple URLs at once
   - Consistent metadata across batches

10. **`list_indexed_content`** - View user-indexed content

11. **`remove_indexed_content`** - Delete indexed URLs

12. **`refresh_all_indexed_content`** - Re-index all user content

### Hybrid Search Engine

The Moveworks server implements a sophisticated **3-stage search pipeline**:

#### Stage 1: Topic Extraction
```python
Query: "How do I configure HTTP actions with authentication?"

Extracted Topics:
- "http action" (compound term)
- "api authentication" (compound term)
- "configure"
- "configure http"
```

#### Stage 2: Multi-Query Search
Each extracted topic is searched independently in parallel, then results are merged and deduplicated.

#### Stage 3: Semantic Search
- Uses `all-MiniLM-L6-v2` model (384-dimensional embeddings)
- Computes cosine similarity between query and documents
- Filters results above threshold (default: 0.5)
- Re-ranks by relevance score

**Result:** Comprehensive, accurate documentation discovery that understands *meaning*, not just keywords.

### Persistent Knowledge Bases

Knowledge bases are stored locally with this structure:

```
~/.moveworks_mcp/knowledge_base/
├── {kb_name}/
│   ├── index.json              # KB metadata & document index
│   ├── config.json             # KB configuration
│   ├── docs/                   # Individual documents
│   │   ├── {doc_id}.json
│   │   └── ...
│   └── embeddings/             # Pre-computed vectors
│       ├── embeddings.json     # Embedding metadata
│       └── vectors/
│           ├── {doc_id}.npy    # NumPy arrays
│           └── ...
```

**Benefits:**
- ⚡ Instant search (no crawling delay)
- 💾 Reduced network traffic
- 🎯 Consistent results
- 🔄 Update control via refresh

---

## Installation

### From GitHub

```bash
# Clone the repository
git clone https://github.com/KarthikeyanM3011/sn_mcp.git
cd sn_mcp/sn_mcp

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install package with dependencies
pip install -e .
```

### Install Semantic Search (Optional but Recommended)

For semantic search capabilities in Moveworks MCP:

```bash
pip install sentence-transformers
```

*Note: The Moveworks server will work without this, but semantic search will be disabled.*

### Verify Installation

```bash
# Check ServiceNow MCP
servicenow-mcp --help

# Check Moveworks MCP
moveworks-mcp --help

# Verify SSE servers
servicenow-mcp-sse --help
moveworks-mcp-sse --help
```

---

## Configuration

### Claude Desktop Integration

Add both servers to Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ServiceNow": {
      "command": "/path/to/your/.venv/bin/python",
      "args": ["-m", "servicenow_mcp.cli"],
      "env": {
        "SERVICENOW_INSTANCE_URL": "https://your-instance.service-now.com",
        "SERVICENOW_USERNAME": "your-username",
        "SERVICENOW_PASSWORD": "your-password",
        "SERVICENOW_AUTH_TYPE": "basic",
        "MCP_TOOL_PACKAGE": "full"
      }
    },
    "Moveworks": {
      "command": "/path/to/your/.venv/bin/python",
      "args": ["-m", "moveworks_mcp.cli"],
      "env": {
        "MOVEWORKS_DOCS_BASE_URL": "https://developer.moveworks.com",
        "MOVEWORKS_DEBUG": "false"
      }
    }
  }
}
```

**Finding your Python path:**
```bash
# While virtual environment is activated:
which python    # macOS/Linux
where python    # Windows
```

### Environment Variables

#### ServiceNow Server

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICENOW_INSTANCE_URL` | Yes | - | ServiceNow instance URL |
| `SERVICENOW_AUTH_TYPE` | Yes | - | Auth type: `basic`, `oauth`, or `api_key` |
| `SERVICENOW_USERNAME` | Conditional | - | Username (basic/oauth) |
| `SERVICENOW_PASSWORD` | Conditional | - | Password (basic/oauth) |
| `SERVICENOW_CLIENT_ID` | Conditional | - | OAuth client ID |
| `SERVICENOW_CLIENT_SECRET` | Conditional | - | OAuth client secret |
| `SERVICENOW_TOKEN_URL` | Conditional | - | OAuth token endpoint |
| `SERVICENOW_API_KEY` | Conditional | - | API key |
| `MCP_TOOL_PACKAGE` | No | `full` | Tool package name |
| `SERVICENOW_DEBUG` | No | `false` | Enable debug logging |
| `SERVICENOW_TIMEOUT` | No | `30` | Request timeout (seconds) |

#### Moveworks Server

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOVEWORKS_DOCS_BASE_URL` | No | `https://developer.moveworks.com` | Base URL for docs |
| `MOVEWORKS_DEBUG` | No | `false` | Enable debug logging |
| `MOVEWORKS_TIMEOUT` | No | `30` | Request timeout (seconds) |

---

## Usage Examples

### ServiceNow Examples

#### Knowledge Base Management

Ask Claude:

```
"Create a new knowledge base called 'IT Support' for the IT department"

"Create a category called 'Network Troubleshooting' in the IT Support KB"

"Write a knowledge article about VPN setup in the Network Troubleshooting category"

"Publish the VPN setup article so users can see it"

"List all published articles in the IT Support knowledge base"
```

#### Table Operations

```
"Show me all available ServiceNow tables"

"Get the schema for the incident table"

"List the last 10 incidents with priority 1"

"Get the full details of incident INC0010001"

"Query the sys_user table for users in the IT department"
```

### Moveworks Examples

#### Quick Documentation Query

```
"What is the Moveworks Creator Studio?"

"How do I create HTTP actions in Moveworks?"

"Explain decision policies in Moveworks workflows"
```

This will use `query_moveworks_docs` to crawl and return fresh content.

#### Build Persistent Knowledge Base

```
"Index the Moveworks documentation into a knowledge base called 'moveworks_dev'"
```

This will:
1. Crawl the documentation site
2. Extract and store content
3. Generate semantic embeddings
4. Save to `~/.moveworks_mcp/knowledge_base/moveworks_dev/`

#### Fast Hybrid Search

```
"Search the moveworks_dev knowledge base for information about HTTP actions"

"Find documentation about authentication in the moveworks_dev KB"
```

Uses the 3-stage hybrid search engine for instant, accurate results.

#### Index External URLs

```
"Index this URL with category 'API' and tags 'rest, authentication':
https://example.com/api-docs"

"Index multiple URLs from our internal documentation site:
- https://internal.example.com/api/rest
- https://internal.example.com/api/webhooks
- https://internal.example.com/api/oauth"
```

#### Manage Knowledge Bases

```
"List all my knowledge bases"

"Show me all documents in the moveworks_dev knowledge base"

"Delete the old_documentation knowledge base"

"Refresh all indexed content to get the latest versions"
```

---

## Deployment Options

### Option 1: Claude Desktop (stdio)

Best for: Individual developers using Claude Desktop

**Configuration:** See [Claude Desktop Integration](#claude-desktop-integration) above

### Option 2: SSE Server (HTTP)

Best for: Web applications, custom integrations, shared access

#### Start ServiceNow SSE Server

```bash
servicenow-mcp-sse \
  --host 0.0.0.0 \
  --port 8080 \
  --instance-url https://your-instance.service-now.com \
  --username your-username \
  --password your-password \
  --auth-type basic
```

#### Start Moveworks SSE Server

```bash
moveworks-mcp-sse \
  --host 0.0.0.0 \
  --port 8001 \
  --docs-base-url https://developer.moveworks.com
```

#### SSE Endpoints

Both servers expose:
- `/sse` - SSE connection endpoint
- `/messages/` - Message sending endpoint

### Option 3: Docker (Coming Soon)

```bash
# Build image
docker build -t sn-moveworks-mcp .

# Run ServiceNow container
docker run -d \
  -e SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com \
  -e SERVICENOW_USERNAME=your-username \
  -e SERVICENOW_PASSWORD=your-password \
  -e SERVICENOW_AUTH_TYPE=basic \
  -p 8080:8080 \
  sn-moveworks-mcp servicenow-mcp-sse
```

---

## Advanced Features

### Custom Tool Packages

Create custom tool combinations by editing `config/tool_packages.yaml`:

```yaml
# Custom package for KB authors who also need table access
kb_with_tables:
  - create_knowledge_base
  - list_knowledge_bases
  - create_category
  - create_article
  - update_article
  - publish_article
  - list_articles
  - get_article
  - list_tables
  - list_records

# Custom package for read-only access
read_only:
  - list_knowledge_bases
  - list_articles
  - get_article
  - list_tables
  - get_table
  - list_records
  - get_record
```

Then use:
```bash
export MCP_TOOL_PACKAGE=kb_with_tables
```

### Semantic Search Tuning

Adjust semantic search sensitivity by modifying the threshold in your code:

```python
# In kb_search.py or your custom implementation
semantic_engine = SemanticSearchEngine(
    similarity_threshold=0.5  # Default
    # Try 0.3 for broader matches
    # Try 0.7 for stricter matches
)
```

### Batch URL Indexing

Create a file `urls.txt`:
```
https://docs.example.com/api/rest
https://docs.example.com/api/webhooks
https://docs.example.com/api/oauth
https://docs.example.com/guides/quickstart
```

Then ask Claude:
```
"Index all URLs from my urls.txt file with category 'API Documentation'"
```

### Knowledge Base Refresh Strategies

**Full Refresh:**
```
"Refresh all indexed content in the moveworks_dev knowledge base"
```

**Selective Refresh:**
```
"Re-index only the authentication documentation in moveworks_dev"
```

---

## Troubleshooting

### ServiceNow Connection Issues

**Problem:** `Authentication failed` error

✅ **Solutions:**
- Verify `SERVICENOW_AUTH_TYPE` matches your credential type
- Check username and password are correct
- Ensure your ServiceNow account has API access enabled
- For OAuth, verify client ID and secret
- Check that password doesn't contain unescaped special characters

**Problem:** `Instance URL not found`

✅ **Solutions:**
- Ensure URL starts with `https://`
- Remove trailing slashes from URL
- Verify instance is accessible in browser
- Check for typos in instance name

### Moveworks Search Issues

**Problem:** Semantic search not working

✅ **Solutions:**
```bash
# Install sentence-transformers
pip install sentence-transformers

# Verify installation
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

**Problem:** Knowledge base creation fails

✅ **Solutions:**
- Check disk space in `~/.moveworks_mcp/`
- Verify write permissions
- Try a different KB name (avoid special characters)
- Check network connectivity to documentation site

**Problem:** Search returns no results

✅ **Solutions:**
- Verify KB was indexed successfully: `"List all documents in {kb_name}"`
- Try broader search terms
- Check if documentation site structure changed
- Re-index the knowledge base

### Performance Issues

**Problem:** Slow search performance

✅ **Solutions:**
- Use indexed KBs instead of real-time crawling
- Enable semantic search for better relevance
- Reduce `max_pages` parameter
- Use tool packages to limit available tools

**Problem:** High memory usage

✅ **Solutions:**
- Delete unused knowledge bases
- Reduce number of indexed documents
- Use streaming for large queries
- Restart MCP servers periodically

### Claude Desktop Integration

**Problem:** Tools not appearing in Claude

✅ **Solutions:**
- Restart Claude Desktop after config changes
- Verify Python path in config is correct: `which python` (with venv active)
- Check config JSON syntax is valid
- Look for errors in Claude Desktop logs:
  - macOS: `~/Library/Logs/Claude/`
  - Windows: `%APPDATA%\Claude\logs\`

**Problem:** Environment variables not working

✅ **Solutions:**
- Ensure `.env` file is in the correct directory
- Check for typos in variable names
- Verify no extra spaces around `=` signs
- Use absolute paths, not relative paths

### Debug Mode

Enable detailed logging:

```bash
# ServiceNow
export SERVICENOW_DEBUG=true

# Moveworks
export MOVEWORKS_DEBUG=true
```

Or add to `.env`:
```bash
SERVICENOW_DEBUG=true
MOVEWORKS_DEBUG=true
```

---

## Project Structure

```
sn_mcp/
├── config/
│   └── tool_packages.yaml          # Tool package definitions
├── src/
│   ├── servicenow_mcp/
│   │   ├── cli.py                  # ServiceNow CLI entry point
│   │   ├── server.py               # ServiceNow MCP server
│   │   ├── server_sse.py           # ServiceNow SSE server
│   │   ├── auth/
│   │   │   └── auth_manager.py     # Multi-method authentication
│   │   ├── tools/
│   │   │   ├── kb_tools.py         # Knowledge base operations
│   │   │   └── table_tools.py      # Table operations
│   │   └── utils/
│   │       ├── config.py           # Configuration models
│   │       └── tool_utils.py       # Tool registry
│   └── moveworks_mcp/
│       ├── cli.py                  # Moveworks CLI entry point
│       ├── server.py               # Moveworks MCP server
│       ├── server_sse.py           # Moveworks SSE server
│       ├── auth/
│       │   └── auth_manager.py     # Minimal auth (public docs)
│       ├── tools/
│       │   ├── docs_crawler.py     # Intelligent documentation crawler
│       │   ├── kb_search.py        # Hybrid search engine
│       │   ├── knowledge_base_manager.py  # KB persistence
│       │   ├── indexer.py          # URL indexing
│       │   ├── embedding_cache.py  # Vector storage
│       │   └── documentation_tools.py  # Query tools
│       └── utils/
│           ├── config.py           # Configuration models
│           └── tool_utils.py       # Tool registry
├── .env.example                    # Environment template
├── pyproject.toml                  # Project metadata & dependencies
├── README.md                       # This file
└── LICENSE                         # MIT License
```

---

## Dependencies

### Core Dependencies

- **mcp[cli]==1.3.0** - Model Context Protocol SDK
- **requests>=2.28.0** - HTTP client for ServiceNow API
- **pydantic>=2.0.0** - Data validation and configuration
- **python-dotenv>=1.0.0** - Environment variable management

### Web & Server

- **starlette>=0.27.0** - ASGI framework for SSE server
- **uvicorn>=0.22.0** - ASGI server
- **httpx>=0.24.0** - Async HTTP client

### Documentation & Search

- **beautifulsoup4>=4.12.0** - HTML parsing and extraction
- **PyYAML>=6.0** - Configuration file parsing
- **sentence-transformers>=2.2.0** - Semantic search embeddings
- **numpy>=1.24.0** - Vector operations and storage

### Development Dependencies

- **pytest>=7.0.0** - Testing framework
- **pytest-cov>=4.0.0** - Code coverage
- **black>=23.0.0** - Code formatting
- **isort>=5.12.0** - Import sorting
- **mypy>=1.0.0** - Type checking
- **ruff>=0.0.1** - Fast Python linter

---

## Contributing

Contributions are welcome! Here's how to get started:

### Development Setup

```bash
# Clone repository
git clone https://github.com/KarthikeyanM3011/sn_mcp.git
cd sn_mcp/sn_mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
isort src/

# Type check
mypy src/

# Lint
ruff check src/
```

### Contribution Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes with tests
4. **Format** code: `black src/ && isort src/`
5. **Test**: `pytest`
6. **Commit**: `git commit -m 'Add amazing feature'`
7. **Push**: `git push origin feature/amazing-feature`
8. **Open** a Pull Request

### Ideas for Contributions

- 🔧 Add new ServiceNow tools (incidents, changes, catalog items)
- 🌐 Support additional documentation sites
- 🎨 Improve search relevance algorithms
- 📊 Add analytics and metrics
- 🐳 Create Docker deployment examples
- 📖 Improve documentation
- 🐛 Fix bugs and improve error handling
- ⚡ Performance optimizations

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built on the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) by Anthropic
- Semantic search powered by [sentence-transformers](https://www.sbert.net/)
- Documentation crawling with [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)

---

## Support & Community

- 🐛 **Report Issues:** [GitHub Issues](https://github.com/KarthikeyanM3011/sn_mcp/issues)
- 💡 **Feature Requests:** [GitHub Discussions](https://github.com/KarthikeyanM3011/sn_mcp/discussions)
- ⭐ **Star this repo** if you find it helpful!
- 🔀 **Fork and extend** for your own use cases

---

## What's Next?

### Roadmap

- [ ] **Additional ServiceNow Tools**
  - Incident management (create, update, resolve)
  - Change request workflows
  - Service catalog integration
  - User and group management

- [ ] **Enhanced Search**
  - Multi-language support
  - Query auto-complete
  - Search result ranking improvements
  - Fuzzy matching

- [ ] **Developer Experience**
  - Docker Compose setup
  - Kubernetes deployment examples
  - Web UI for KB management
  - Interactive documentation

- [ ] **Performance**
  - Incremental indexing
  - Parallel crawling
  - Caching improvements
  - Connection pooling

---

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search [existing issues](https://github.com/KarthikeyanM3011/sn_mcp/issues)
3. Enable debug mode and check logs
4. Open a new issue with:
   - Your environment (OS, Python version)
   - Steps to reproduce
   - Error messages
   - Configuration (sanitized)

---

**Made with ❤️ for the Claude AI and MCP community**

*Empowering AI assistants with enterprise integrations and intelligent documentation search*
