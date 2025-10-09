import logging
import asyncio
import time
from typing import Optional, Callable
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from uvicorn.logging import DefaultFormatter

from .agentcore_client import AgentCoreClient
from .a2a_proxy_server import refresh_agents
from .a2a_proxy_server import app as base_app
from .config import get_config

# Load configuration
config = get_config()

# ANSI color codes for logging
BRIGHT_WHITE = "\033[1;37m"
DIM_GREY = "\033[90m"
RESET = "\033[0m"

# Configure our application logger with uvicorn's style
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(getattr(logging, config.log_level, logging.INFO))
logger.propagate = False


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware for HTTP access logging"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(f'{request.method} {request.url.path} {response.status_code} {duration:.3f}s')
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f'{request.method} {request.url.path} failed after {duration:.3f}s: {e}')
            raise


def log_startup_config():
    """Log configuration settings on startup"""
    logger.info("Starting AWS Bedrock AgentCore A2A Proxy")
    logger.info("Configuration:")
    logger.info(f"• Agent Refresh Interval: {config.agent_refresh_interval_seconds}s")
    logger.info(f"• Streaming Enabled: {config.enable_streaming}")
    logger.info(f"• Description as A2A Skill: {config.enable_description_as_a2a_skill}")
    logger.info(f"• Server: http://{config.host}:{config.port}")
    if config.host != config.expose_host or config.port != config.expose_port:
        logger.info(f"• External URL: {config.get_base_url()}")


async def agent_polling_task():
    """Background task that polls for agent changes."""

    while True:
        try:
            await asyncio.sleep(config.agent_refresh_interval_seconds)
            agents = await refresh_agents()

            # Show polling result in one line
            if agents:
                formatted_names = []
                for agent in agents:
                    name = agent.get("agentRuntimeName", f"agent-{agent.get('agentRuntimeId')}")
                    version = agent.get("agentRuntimeVersion", "1")
                    formatted_names.append(f"{BRIGHT_WHITE}{name}{RESET}{DIM_GREY} (v{version}){RESET}")
                logger.info(f"polling: discovered {len(agents)} agents: {', '.join(formatted_names)}")
            else:
                logger.info("polling: discovered 0 agents")

        except Exception as e:
            logger.error(f"error during agent polling: {e}")
            # Continue polling even if one iteration fails


@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager"""
    log_startup_config()
    logger.info(f"API Docs: http://{config.host}:{config.port}/docs")

    # Initial agent discovery
    agents = await refresh_agents()

    # Show startup result
    if agents:
        formatted_names = []
        for agent in agents:
            name = agent.get("agentRuntimeName", f"agent-{agent.get('agentRuntimeId')}")
            version = agent.get("agentRuntimeVersion", "1")
            formatted_names.append(f"{BRIGHT_WHITE}{name}{RESET}{DIM_GREY} (v{version}){RESET}")
        logger.info(f"polling: discovered {len(agents)} agents: {', '.join(formatted_names)}")
    else:
        logger.info("polling: discovered 0 agents")

    # Start background polling task
    polling_task = asyncio.create_task(agent_polling_task())

    yield

    # Shutdown
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    logger.info("Shutting down A2A proxy")
    app.state.agents.clear()
    logger.info("A2A proxy shutdown complete")


def create_app(on_agents_refresh: Optional[Callable] = None):
    """Set up the FastAPI app with state and middleware."""

    # Set up app state
    base_app.state.config = config
    base_app.state.client = AgentCoreClient()
    base_app.state.agents = {}
    base_app.state.on_agents_refresh = on_agents_refresh

    # Set up lifespan
    base_app.router.lifespan_context = lifespan

    # Add access logging middleware
    base_app.add_middleware(AccessLogMiddleware)

    # Add CORS middleware to support web-based A2A clients
    base_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return base_app


# App will be created by uvicorn using --factory flag


# For programmatic startup
if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=config.host, port=config.port)
