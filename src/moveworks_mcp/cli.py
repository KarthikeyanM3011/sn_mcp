import argparse
import logging
import os
import sys

import anyio
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server

from moveworks_mcp.server import MoveworksMCP
from moveworks_mcp.utils.config import ServerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Moveworks MCP Server")

    # Server configuration
    parser.add_argument(
        "--docs-base-url",
        help="Moveworks documentation base URL",
        default=os.environ.get("MOVEWORKS_DOCS_BASE_URL", "https://help.moveworks.com/docs"),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
        default=os.environ.get("MOVEWORKS_DEBUG", "false").lower() == "true",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout in seconds",
        default=int(os.environ.get("MOVEWORKS_TIMEOUT", "30")),
    )

    return parser.parse_args()


def create_config(args) -> ServerConfig:
    return ServerConfig(
        docs_base_url=args.docs_base_url,
        debug=args.debug,
        timeout=args.timeout,
    )


async def arun_server(server_instance):
    logger.info("Starting Moveworks MCP server with stdio transport...")
    async with stdio_server() as streams:
        init_options = server_instance.create_initialization_options()
        await server_instance.run(streams[0], streams[1], init_options)
    logger.info("Stdio server finished.")


def main():
    load_dotenv()

    try:
        args = parse_args()

        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled.")
        else:
            logging.getLogger().setLevel(logging.INFO)

        config = create_config(args)
        logger.info(f"Initializing Moveworks MCP server with docs URL: {config.docs_base_url}")

        mcp_controller = MoveworksMCP(config)

        server_to_run = mcp_controller.start()

        anyio.run(arun_server, server_to_run)

    except ValueError as e:
        logger.error(f"Configuration or runtime error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Unexpected error starting or running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
