import json
import logging
from typing import Any, Dict, List, Union

import mcp.types as types
from mcp.server.lowlevel import Server
from pydantic import ValidationError

from moveworks_mcp.auth.auth_manager import AuthManager
from moveworks_mcp.utils.config import ServerConfig
from moveworks_mcp.utils.tool_utils import get_tool_definitions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def serialize_tool_output(result: Any, tool_name: str) -> str:
    """Serializes tool output to a string, preferably JSON indented."""
    try:
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                return result  
        elif isinstance(result, dict):
            return json.dumps(result, indent=2)
        elif hasattr(result, "model_dump_json"):
            try:
                return result.model_dump_json(indent=2)
            except TypeError:  
                return json.dumps(result.model_dump(), indent=2)
        elif hasattr(result, "model_dump"):  
            return json.dumps(result.model_dump(), indent=2)
        elif hasattr(result, "dict"): 
            return json.dumps(result.dict(), indent=2)
        else:
            logger.warning(
                f"Could not serialize result for tool '{tool_name}' to JSON, falling back to str(). Type: {type(result)}"
            )
            return str(result)
    except Exception as e:
        logger.error(f"Error during serialization for tool '{tool_name}': {e}", exc_info=True)
        return json.dumps(
            {"error": f"Serialization failed for tool {tool_name}", "details": str(e)}, indent=2
        )


class MoveworksMCP:

    def __init__(self, config: Union[Dict, ServerConfig]):
        if isinstance(config, dict):
            self.config = ServerConfig(**config)
        else:
            self.config = config

        self.auth_manager = AuthManager()
        self.mcp_server = Server("Moveworks")  
        self.name = "Moveworks"

        self.tool_definitions = get_tool_definitions()

        self._register_handlers()

    def _register_handlers(self):
        self.mcp_server.list_tools()(self._list_tools_impl)
        self.mcp_server.call_tool()(self._call_tool_impl)
        logger.info("Registered list_tools and call_tool handlers.")

    async def _list_tools_impl(self) -> List[types.Tool]:
        tool_list: List[types.Tool] = []

        for tool_name, definition in self.tool_definitions.items():
            _impl_func, params_model, _return_annotation, description, _serialization = definition
            try:
                schema = params_model.model_json_schema()
                tool_list.append(
                    types.Tool(name=tool_name, description=description, inputSchema=schema)
                )
            except Exception as e:
                logger.error(
                    f"Failed to generate schema for tool '{tool_name}': {e}", exc_info=True
                )

        logger.debug(f"Listing {len(tool_list)} tools for Moveworks MCP server.")
        return tool_list

    async def _call_tool_impl(self, name: str, arguments: dict) -> list[types.TextContent]:
        logger.info(f"Received call_tool request for tool '{name}'")

        if name not in self.tool_definitions:
            raise ValueError(f"Unknown tool: {name}")

        definition = self.tool_definitions[name]
        impl_func, params_model, _return_annotation, _description, _serialization = definition

        try:
            params = params_model(**arguments)
            logger.debug(f"Parsed arguments for tool '{name}': {params}")
        except ValidationError as e:
            logger.error(f"Invalid arguments for tool '{name}': {e}", exc_info=True)
            raise ValueError(f"Invalid arguments for tool '{name}': {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error parsing arguments for tool '{name}': {e}", exc_info=True
            )
            raise ValueError(f"Failed to parse arguments for tool '{name}': {e}")

        try:
            result = impl_func(self.config, self.auth_manager, params)
            logger.debug(f"Raw result type from tool '{name}': {type(result)}")
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            raise RuntimeError(f"Error during execution of tool '{name}': {e}") from e

        serialized_string = serialize_tool_output(result, name)
        logger.debug(f"Serialized value for tool '{name}': {serialized_string[:500]}...")

        return [types.TextContent(type="text", text=serialized_string)]

    def start(self) -> Server:
        logger.info(
            "MoveworksMCP instance configured. Returning low-level server instance for external execution."
        )
        return self.mcp_server
