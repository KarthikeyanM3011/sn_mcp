import argparse
import logging
import os
import sys

import anyio
from dotenv import load_dotenv
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

from moveworks_mcp.server import MoveworksMCP
from moveworks_mcp.utils.config import ServerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Moveworks MCP SSE Server")

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
    parser.add_argument(
        "--host",
        help="Server host",
        default=os.environ.get("MOVEWORKS_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Server port",
        default=int(os.environ.get("MOVEWORKS_PORT", "8001")),
    )

    return parser.parse_args()


def create_config(args) -> ServerConfig:
    return ServerConfig(
        docs_base_url=args.docs_base_url,
        debug=args.debug,
        timeout=args.timeout,
    )


async def handle_sse(request):
    async with SseServerTransport("/messages") as transport:
        init_options = mcp_server.create_initialization_options()
        await mcp_server.run(
            transport.read_stream,
            transport.write_stream,
            init_options,
        )


async def handle_messages(request):
    async with SseServerTransport("/messages") as transport:
        init_options = mcp_server.create_initialization_options()
        await mcp_server.run(
            transport.read_stream,
            transport.write_stream,
            init_options,
        )


def main():
    global mcp_server

    load_dotenv()

    try:
        args = parse_args()

        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled.")
        else:
            logging.getLogger().setLevel(logging.INFO)

        config = create_config(args)
        logger.info(f"Initializing Moveworks MCP SSE server with docs URL: {config.docs_base_url}")

        mcp_controller = MoveworksMCP(config)

        mcp_server = mcp_controller.start()

        app = Starlette(
            debug=args.debug,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=handle_messages, methods=["POST"]),
            ],
        )

        import uvicorn
        logger.info(f"Starting SSE server on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)

    except ValueError as e:
        logger.error(f"Configuration or runtime error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Unexpected error starting or running SSE server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
