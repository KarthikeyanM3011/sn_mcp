# ServiceNow MCP Server

**Connect Claude AI to your ServiceNow instance** - Manage incidents, catalog items, change requests, and more using natural language.

## What is this?

This MCP (Model Context Protocol) server lets you use Claude AI to interact with ServiceNow through simple, natural language conversations. Instead of navigating through ServiceNow's web interface, you can ask Claude to:

- Create and manage incidents
- Browse and organize the service catalog
- Handle change requests and approvals
- Manage knowledge articles
- Administer users and groups
- And much more!

**Example:** Just ask Claude: *"Create a high priority incident for a network outage in the east region"* and it will do it for you.

## What is MCP?

MCP (Model Context Protocol) is a standard that allows AI assistants like Claude to securely connect to external services and tools. Think of it as a bridge that lets Claude safely interact with your ServiceNow instance on your behalf.

## Key Capabilities

### 🎫 Incident Management
Create, update, resolve, and track incidents with simple commands

### 📦 Service Catalog
Browse items, manage categories, create variables, and optimize your catalog

### 🔄 Change Management
Create change requests, add tasks, manage approvals, and track implementation

### 📚 Knowledge Base
Create knowledge bases, organize articles, and publish content

### 👥 User & Group Management
Create users, manage groups, and handle permissions

### 📋 Agile Management
Manage user stories, epics, scrum tasks, and projects

### ⚙️ Advanced Features
- Workflow development and management
- Script includes for server-side scripting
- Changeset management for deployments
- UI policies for dynamic forms
- Multiple authentication methods (Basic, OAuth, API Key)
- Debug mode for troubleshooting

---

## Quick Start

### What You'll Need

- **Python 3.11 or higher** installed on your computer
- **A ServiceNow instance** with login credentials
- **5 minutes** to set everything up

### Installation Steps

**Step 1: Get the code**
```bash
git clone https://github.com/echelon-ai-labs/servicenow-mcp.git
cd servicenow-mcp
```

**Step 2: Set up Python environment**
```bash
# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

**Step 3: Configure your ServiceNow connection**

Create a file named `.env` in the project folder with your ServiceNow details:

```bash
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic
```

> **Note:** Replace the values with your actual ServiceNow instance URL and credentials

**Step 4: Test it out!**

```bash
python -m servicenow_mcp.cli
```

If you see no errors, you're all set! 🎉

---

## Connecting to Claude Desktop

The easiest way to use this server is with Claude Desktop. Here's how:

**Step 1: Find your config file**

The configuration file location depends on your operating system:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

**Step 2: Add the ServiceNow MCP server**

Edit the configuration file and add this (update the paths to match your setup):

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
        "SERVICENOW_AUTH_TYPE": "basic"
      }
    }
  }
}
```

> **Finding your Python path:** Run `which python` (macOS/Linux) or `where python` (Windows) while your virtual environment is activated

**Step 3: Restart Claude Desktop**

Close and reopen Claude Desktop. You should now see ServiceNow tools available!

**Step 4: Try it out**

Start a conversation with Claude and try something like:
> "List all high priority incidents assigned to the Network team"

---

## Authentication Methods

Choose the authentication method that works best for your ServiceNow instance:

### Option 1: Basic Authentication (Easiest)

```bash
SERVICENOW_AUTH_TYPE=basic
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

### Option 2: OAuth (More Secure)

```bash
SERVICENOW_AUTH_TYPE=oauth
SERVICENOW_CLIENT_ID=your-client-id
SERVICENOW_CLIENT_SECRET=your-client-secret
SERVICENOW_TOKEN_URL=https://your-instance.service-now.com/oauth_token.do
```

### Option 3: API Key

```bash
SERVICENOW_AUTH_TYPE=api_key
SERVICENOW_API_KEY=your-api-key
```

---

## Advanced Usage

### Running as a Standalone Server (SSE Mode)

For advanced integrations, you can run the MCP server as a web service using Server-Sent Events:

```bash
servicenow-mcp-sse --instance-url=https://your-instance.service-now.com \
                   --username=your-username \
                   --password=your-password
```

**Custom host and port:**
```bash
servicenow-mcp-sse --host=127.0.0.1 --port=8000
```

The server exposes two endpoints:
- `/sse` - SSE connection endpoint
- `/messages/` - Message sending endpoint

**Example Python code:**
```python
from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.server_sse import create_starlette_app
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
import uvicorn

config = ServerConfig(
    instance_url="https://your-instance.service-now.com",
    auth=AuthConfig(
        type=AuthType.BASIC,
        config=BasicAuthConfig(
            username="your-username",
            password="your-password"
        )
    ),
    debug=True
)

servicenow_mcp = ServiceNowMCP(config)
app = create_starlette_app(servicenow_mcp, debug=True)
uvicorn.run(app, host="0.0.0.0", port=8080)
```

See `examples/sse_server_example.py` for a complete example.

---

## Tool Packages (Role-Based Access)

By default, this server provides **all available tools** to Claude. However, you can limit which tools are available based on specific roles or use cases.

### Why Use Tool Packages?

- **Simplify the experience** - Only show tools relevant to a specific role
- **Reduce token usage** - Fewer tools means less context for Claude to process
- **Improve focus** - Help Claude choose the right tools faster

### How to Use

Set the `MCP_TOOL_PACKAGE` environment variable to choose a package:

```bash
export MCP_TOOL_PACKAGE=service_desk
```

Or add it to your `.env` file:
```bash
MCP_TOOL_PACKAGE=service_desk
```

### Available Packages

| Package | Best For | What's Included |
|---------|----------|----------------|
| `full` | Everyone (default) | All available tools |
| `service_desk` | Help desk agents | Incident management, user lookup, knowledge articles |
| `catalog_builder` | Catalog administrators | Catalog items, categories, variables, UI policies |
| `change_coordinator` | Change managers | Change requests, tasks, approvals |
| `knowledge_author` | Knowledge managers | Knowledge bases, categories, articles |
| `platform_developer` | Developers | Script includes, workflows, changesets |
| `system_administrator` | System admins | User/group management, system logs |
| `agile_management` | Scrum teams | User stories, epics, scrum tasks, projects |
| `none` | Testing | No tools (except `list_tool_packages`) |

### Customizing Packages

You can create your own custom packages by editing `config/tool_packages.yaml`. The file uses a simple YAML format where you define which tools belong to each package.

### Finding Available Packages

Claude can list all available packages for you. Just ask:
> "What tool packages are available?"

---

## What Can You Do With This?

Instead of listing all 80+ tools, here are real-world examples of what you can accomplish:

### 🎫 Incident Management
Ask Claude things like:
- *"Create a new incident for a network outage in the east region"*
- *"Update incident INC0010001 to high priority"*
- *"Add a comment to incident INC0010001 saying we're investigating"*
- *"Resolve incident INC0010001 - the server was restarted"*
- *"Show me all P1 incidents assigned to the Network team"*

### 📦 Service Catalog
- *"List all items in the service catalog"*
- *"Create a new category called 'Cloud Services'"*
- *"Move the laptop request item to the Hardware category"*
- *"Add a dropdown field for laptop models to the laptop request form"*
- *"Analyze our service catalog and suggest improvements"*

### 🔄 Change Management
- *"Create a change request for server maintenance tomorrow night"*
- *"Add a pre-implementation checklist task to the maintenance change"*
- *"Submit the server maintenance change for approval"*
- *"Show me all emergency changes scheduled this week"*
- *"Approve change CHG0012345 with comment 'Looks good to proceed'"*

### 📚 Knowledge Management
- *"Create a knowledge base for the IT department"*
- *"Create a category called 'Network Troubleshooting'"*
- *"Write an article about VPN setup in the Network category"*
- *"Publish the VPN article so users can see it"*
- *"Find all articles about password reset"*

### 👥 User & Group Management
- *"Create a new user Alice in the Radiology department"*
- *"Add the ITIL role to Bob's account"*
- *"Create a group called 'Biomedical Engineering'"*
- *"Add Alice and Bob to the Biomedical Engineering group"*
- *"List all users in the IT department"*

### 📋 Agile Management
- *"Create a user story for implementing a new reporting dashboard"*
- *"Create an epic called 'Data Analytics Initiatives'"*
- *"List all user stories assigned to the Data team"*
- *"Create a scrum task for the reporting dashboard story"*
- *"Mark the data extraction task as completed"*

### ⚙️ Advanced Development
- *"Show me all active workflows in ServiceNow"*
- *"Create a workflow for handling software license requests"*
- *"List all script includes in the system"*
- *"Create a changeset for the HR Portal application"*
- *"Create a UI policy that shows justification when cost > $100"*

<details>
<summary><b>📋 Complete Tool List (Click to expand)</b></summary>

### Incident Management (5 tools)
- `create_incident`, `update_incident`, `add_comment`, `resolve_incident`, `list_incidents`

### Service Catalog (12 tools)
- `list_catalog_items`, `get_catalog_item`, `update_catalog_item`
- `list_catalog_categories`, `create_catalog_category`, `update_catalog_category`
- `move_catalog_items`, `list_catalogs`
- `create_catalog_item_variable`, `list_catalog_item_variables`, `update_catalog_item_variable`
- `get_optimization_recommendations`

### Change Management (8 tools)
- `create_change_request`, `update_change_request`, `list_change_requests`
- `get_change_request_details`, `add_change_task`
- `submit_change_for_approval`, `approve_change`, `reject_change`

### Agile Management (11 tools)
- **Stories:** `create_story`, `update_story`, `list_stories`, `create_story_dependency`, `delete_story_dependency`
- **Epics:** `create_epic`, `update_epic`, `list_epics`
- **Tasks:** `create_scrum_task`, `update_scrum_task`, `list_scrum_tasks`
- **Projects:** `create_project`, `update_project`, `list_projects`

### Knowledge Base (8 tools)
- `create_knowledge_base`, `list_knowledge_bases`
- `create_category`, `create_article`, `update_article`, `publish_article`
- `list_articles`, `get_article`

### User Management (9 tools)
- `create_user`, `update_user`, `get_user`, `list_users`
- `create_group`, `update_group`, `list_groups`
- `add_group_members`, `remove_group_members`

### Workflow Management (5 tools)
- `list_workflows`, `get_workflow`, `create_workflow`, `update_workflow`, `delete_workflow`

### Script Includes (5 tools)
- `list_script_includes`, `get_script_include`, `create_script_include`
- `update_script_include`, `delete_script_include`

### Changeset Management (7 tools)
- `list_changesets`, `get_changeset_details`, `create_changeset`, `update_changeset`
- `commit_changeset`, `publish_changeset`, `add_file_to_changeset`

### UI Policies (2 tools)
- `create_ui_policy`, `create_ui_policy_action`

**Total: 80+ tools across all categories**

</details>

---

## Alternative: Using MCP CLI

If you have the MCP CLI installed, you can register the server with one command:

```bash
mcp install src/servicenow_mcp/server.py -f .env
```

This automatically registers the ServiceNow MCP server with Claude using your `.env` file configuration.

---

## Troubleshooting

### Connection Issues

**Problem:** Claude can't connect to ServiceNow
- ✅ Verify your instance URL is correct (should start with `https://`)
- ✅ Check your username and password are correct
- ✅ Ensure your ServiceNow account has API access enabled
- ✅ Try testing your credentials directly in a browser

**Problem:** "Authentication failed" error
- ✅ Verify `SERVICENOW_AUTH_TYPE` matches your credential type (`basic`, `oauth`, or `api_key`)
- ✅ For OAuth, ensure your client ID and secret are correct
- ✅ Check that your password doesn't have special characters that need escaping

### Server Issues

**Problem:** Server won't start
- ✅ Ensure Python 3.11+ is installed: `python --version`
- ✅ Verify virtual environment is activated (you should see `.venv` in your prompt)
- ✅ Try reinstalling: `pip install -e . --force-reinstall`

**Problem:** Tools not appearing in Claude
- ✅ Restart Claude Desktop after configuration changes
- ✅ Check the path to Python in your config file is correct
- ✅ Look for errors in Claude Desktop logs

### Getting Help

If you're still stuck:
1. Check the [GitHub Issues](https://github.com/echelon-ai-labs/servicenow-mcp/issues) for similar problems
2. Enable debug mode by adding `"debug": true` to your config
3. Review the detailed documentation in the [`docs`](docs/) directory

---

## Example Scripts

The repository includes working example scripts to help you get started:

| Script | What It Does |
|--------|-------------|
| [`examples/catalog_optimization_example.py`](examples/catalog_optimization_example.py) | Analyzes and suggests improvements for your service catalog |
| [`examples/change_management_demo.py`](examples/change_management_demo.py) | Demonstrates creating and managing change requests |
| [`examples/sse_server_example.py`](examples/sse_server_example.py) | Shows how to run the server in SSE mode |

---

## Additional Documentation

Detailed guides are available in the [`docs`](docs/) directory:

- 📦 [**Catalog Integration**](docs/catalog.md) - Deep dive into Service Catalog features
- 🔄 [**Change Management**](docs/change_management.md) - Complete guide to change request handling
- ⚙️ [**Workflow Management**](docs/workflow_management.md) - Building and managing workflows
- 📋 [**Changeset Management**](docs/changeset_management.md) - Deployment and version control
- 🎯 [**Catalog Optimization**](docs/catalog_optimization_plan.md) - Strategies for improving your catalog

---

## Contributing

We welcome contributions! Here's how to get involved:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to your branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Contribution Ideas
- Add new tools for ServiceNow modules
- Improve error handling and validation
- Add more example scripts
- Enhance documentation
- Report bugs or suggest features

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## Support & Community

- 🐛 **Report Bugs:** [GitHub Issues](https://github.com/echelon-ai-labs/servicenow-mcp/issues)
- 💡 **Feature Requests:** [GitHub Discussions](https://github.com/echelon-ai-labs/servicenow-mcp/discussions)
- 📖 **Documentation:** [docs/](docs/) directory
- ⭐ **Star us on GitHub** if you find this helpful!

---

Made with ❤️ by the ServiceNow MCP community
