import logging
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from uvicorn.logging import DefaultFormatter

from .agentcore_client import AgentCoreClient
from .a2a_proxy_server import A2AProxy
from .config import get_config

load_dotenv()

# ANSI color codes for logging
BRIGHT_WHITE = "\033[1;37m"
DIM_GREY = "\033[90m"
RESET = "\033[0m"

# Configure our application logger with uvicorn's style
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# Load configuration
config = get_config()


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


async def discover_and_refresh_agents(app: FastAPI, is_startup: bool = False) -> Dict[str, Any]:
    """Discover agents and refresh proxy configuration"""

    if hasattr(app.state, "client"):
        client = app.state.client
    else:
        client = AgentCoreClient()
        app.state.client = client

    agents = await client.list_agents()

    if not hasattr(app.state, "proxy"):
        app.state.proxy = A2AProxy(client, config)

    proxy = app.state.proxy
    proxy.agents.clear()
    await proxy.initialize_agents(agents)
    app.state.agents = agents

    try:
        on_agents_refresh_handler = getattr(app.state, "on_agents_refresh_handler", None)
        if on_agents_refresh_handler:
            await on_agents_refresh_handler(agents)
    except Exception as e:
        logger.error(f"Failed to call external handler: {e}")

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

    return {
        "message": "Agent discovery completed",
        "agents_discovered": len(agents),
        "agents": agents,
    }


async def agent_polling_task(app: FastAPI):
    """Background task that polls for agent changes"""

    while True:
        try:
            await asyncio.sleep(config.agent_refresh_interval_seconds)
            await discover_and_refresh_agents(app, is_startup=False)
        except Exception as e:
            logger.error(f"error during agent polling: {e}")
            # Continue polling even if one iteration fails


async def aws_proxy_startup(app: FastAPI):
    """AWS proxy startup logic that can be called from any lifespan."""
    log_startup_config()
    logger.info(f"API Docs: http://{config.host}:{config.port}/docs")

    # Initial agent discovery
    await discover_and_refresh_agents(app, is_startup=True)

    # Start background polling task
    polling_task = asyncio.create_task(agent_polling_task(app))
    app.state.aws_polling_task = polling_task


async def aws_proxy_shutdown(app: FastAPI):
    """AWS proxy shutdown logic that can be called from any lifespan."""
    # Cancel polling task
    if hasattr(app.state, "aws_polling_task"):
        app.state.aws_polling_task.cancel()
        try:
            await app.state.aws_polling_task
        except asyncio.CancelledError:
            pass

    # Shutdown the A2A proxy
    if hasattr(app.state, "proxy"):
        await app.state.proxy.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await aws_proxy_startup(app)
    yield
    await aws_proxy_shutdown(app)


def create_a2a_router() -> APIRouter:
    """Create the A2A router - creates a new proxy router."""
    proxy = A2AProxy(config=config)
    return proxy.get_router()


def create_main_router() -> APIRouter:
    """Create the main AWS proxy router for embedding in other apps."""
    router = APIRouter()

    @router.get("/")
    async def root():
        return {"message": "AWS Bedrock AgentCore A2A Server is running"}

    @router.get("/status")
    async def status(request):
        """Get server status"""
        agents = getattr(request.app.state, "agents", [])
        return {
            "agents_discovered": len(agents),
            "agents": [{"agent_id": agent.get("agentRuntimeId", "")} for agent in agents],
        }

    @router.get("/health")
    async def health():
        return {"status": "healthy"}

    @router.get("/ready")
    async def ready(request: Request):
        """Check if server can connect to AWS"""
        try:
            if not hasattr(request.app.state, "client"):
                raise HTTPException(status_code=503, detail="AWS client not initialized")

            # Test AWS connectivity by listing agents
            agents = await request.app.state.client.list_agents()
            return {"status": "ready", "aws_connection": "ok", "agents_available": len(agents)}
        except Exception as e:
            logger.error(f"AWS connectivity check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")

    return router


def create_app(enable_lifespan: bool = True) -> FastAPI:
    """Create and configure the FastAPI application for standalone use."""
    app = FastAPI(
        title="AWS Bedrock AgentCore A2A Server",
        description="Creates A2A proxy servers for each AWS Bedrock AgentCore agent",
        lifespan=lifespan if enable_lifespan else None,
    )

    # Add CORS middleware to support web-based A2A clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(create_main_router())
    app.include_router(create_a2a_router())

    return app


# Create the app instance for uvicorn
app = create_app()
