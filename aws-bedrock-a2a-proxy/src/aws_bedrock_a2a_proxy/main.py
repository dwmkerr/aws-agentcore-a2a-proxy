import os
import logging
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .agentcore_client import AgentCoreClient
from .a2a_proxy_server import A2AProxy

load_dotenv()


# Configure logging with custom format
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelname == "INFO":
            return f"\033[32mINFO\033[0m:     {record.getMessage()}"
        elif record.levelname == "ERROR":
            return f"\033[31mERROR\033[0m:    {record.getMessage()}"
        elif record.levelname == "WARNING":
            return f"\033[33mWARNING\033[0m:  {record.getMessage()}"
        else:
            return f"{record.levelname}:    {record.getMessage()}"


# Configure only AWS proxy loggers (don't modify global config)
logging.getLogger("aws_bedrock_a2a_proxy.agentcore_client").setLevel(logging.WARNING)
logging.getLogger("aws_bedrock_a2a_proxy.a2a_proxy_server").setLevel(logging.WARNING)

# Our main logger with custom format
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.handlers = [handler]
logger.propagate = False

# Configuration
AGENT_REFRESH_INTERVAL_SECONDS = int(os.getenv("AGENT_REFRESH_INTERVAL_SECONDS", "30"))  # seconds
ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "true").lower() in ("true", "1", "yes")
ENABLE_DESCRIPTION_AS_A2A_SKILL = os.getenv("ENABLE_DESCRIPTION_AS_A2A_SKILL", "1") == "1"
HOST = os.getenv("HOST", "localhost")  # Binding address
PORT = int(os.getenv("PORT", "2972"))  # Binding port
EXPOSE_HOST = os.getenv("EXPOSE_HOST", HOST)  # Advertised host (defaults to HOST)
EXPOSE_PORT = int(os.getenv("EXPOSE_PORT", PORT))  # Advertised port (defaults to PORT)
BASE_PATH = os.getenv("BASE_PATH", "")
A2ASERVER_NAMESPACE = os.getenv("A2ASERVER_NAMESPACE", "default")


def get_server_config() -> Dict[str, Any]:
    """Get server configuration for uvicorn."""
    return {"host": HOST, "port": PORT, "reload": True}  # Enable reload for development


def print_startup_config():
    """Print configuration settings on startup"""
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    logger.info("🚀 Starting AWS Bedrock AgentCore A2A Proxy")
    logger.info("📋 Configuration:")
    logger.info(f"   AWS Region: {aws_region}")
    logger.info(f"   Agent Refresh Interval: {AGENT_REFRESH_INTERVAL_SECONDS}s")
    logger.info(f"   Streaming Enabled: {ENABLE_STREAMING}")
    logger.info(f"   Description as A2A Skill: {ENABLE_DESCRIPTION_AS_A2A_SKILL}")
    logger.info(f"   Server: http://{HOST}:{PORT}")


async def discover_and_refresh_agents(app: FastAPI, is_startup: bool = False) -> Dict[str, Any]:
    """Discover agents and refresh proxy configuration"""

    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Use existing client if available, otherwise create new one
    if hasattr(app.state, "client"):
        client = app.state.client
    else:
        try:
            client = AgentCoreClient(region=aws_region)
            app.state.client = client
        except Exception as e:
            if is_startup:
                logger.error(f"AWS connection failed during startup: {e}")
                logger.info("Server will start without AWS connectivity - check AWS credential chain configuration")
                app.state.client = None
                app.state.agents = []
                # Use global proxy
                app.state.proxy = _global_proxy
                return {
                    "message": "Server started without AWS connectivity",
                    "agents_discovered": 0,
                    "region": aws_region,
                    "agents": [],
                    "error": str(e),
                }
            else:
                raise

    # Discover agents
    try:
        agents = await client.list_agents()
    except Exception as e:
        if is_startup:
            logger.error(f"Agent discovery failed during startup: {e}")
            logger.info("Server will start without agents - check AWS credentials and connectivity")
            agents = []
        else:
            logger.error(f"error during agent polling: {e}")
            return {
                "message": "Agent discovery failed",
                "agents_discovered": 0,
                "region": aws_region,
                "agents": [],
                "error": str(e),
            }

    # Clear existing agents and reinitialize
    if hasattr(app.state, "proxy"):
        proxy = app.state.proxy
        # Clear existing agents from proxy
        proxy.agents.clear()
    else:
        _global_proxy.client = client
        app.state.proxy = _global_proxy

    # Initialize agents in proxy
    proxy = app.state.proxy
    await proxy.initialize_agents(agents)
    app.state.agents = agents

    # Call external handler if provided
    try:
        # Check for external handler (e.g., from wrapper service)
        on_agents_refresh_handler = getattr(app.state, "on_agents_refresh_handler", None)

        if on_agents_refresh_handler:
            await on_agents_refresh_handler(agents)
    except Exception as e:
        logger.error(f"Failed to call external handler: {e}")

    # Show polling result in one line
    if agents:
        # Format agent names with versions: name(version) in bright white with grey version
        formatted_names = []
        for agent in agents:
            name = agent.get("agentRuntimeName", f"agent-{agent.get('agentRuntimeId')}")
            version = agent.get("agentRuntimeVersion", "1")
            formatted_names.append(f"\033[1;37m{name}\033[0m\033[90m (v{version})\033[0m")
        logger.info(f"polling: discovered {len(agents)} agents: {', '.join(formatted_names)}")
    else:
        logger.info("polling: discovered 0 agents")

    return {
        "message": "Agent discovery completed",
        "agents_discovered": len(agents),
        "region": aws_region,
        "agents": agents,
    }


async def agent_polling_task(app: FastAPI):
    """Background task that polls for agent changes"""

    while True:
        try:
            await asyncio.sleep(AGENT_REFRESH_INTERVAL_SECONDS)
            await discover_and_refresh_agents(app, is_startup=False)
        except Exception as e:
            logger.error(f"error during agent polling: {e}")
            # Continue polling even if one iteration fails


async def aws_proxy_startup(app: FastAPI):
    """AWS proxy startup logic that can be called from any lifespan."""
    print_startup_config()
    print(f"\033[32mINFO\033[0m:     API Docs:    \033[34mhttp://{HOST}:{PORT}/docs\033[0m")

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


# Global proxy instance for sharing state
_global_proxy = A2AProxy(None)


def create_a2a_router() -> APIRouter:
    """Create the A2A router - returns the global proxy router."""
    return _global_proxy.get_router()


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


# Create the app instance for uvicorn (maintains backward compatibility)
app = create_app()


# Expose initialization functions for manual setup when mounted
async def init_proxy_app(app: FastAPI):
    """Initialize the proxy app manually (for when mounted in another app)"""
    await discover_and_refresh_agents(app, is_startup=True)
    polling_task = asyncio.create_task(agent_polling_task(app))
    app.state.polling_task = polling_task
    return polling_task
