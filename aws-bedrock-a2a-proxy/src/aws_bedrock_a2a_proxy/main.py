import os
import logging
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from .agentcore_client import AgentCoreClient
from .a2a_proxy import A2AProxy

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


# Configure logging - suppress verbose logs from other modules
logging.basicConfig(level=logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("aws_bedrock_a2a_proxy.agentcore_client").setLevel(logging.WARNING)
logging.getLogger("aws_bedrock_a2a_proxy.a2a_proxy").setLevel(logging.WARNING)

# Our main logger with custom format
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.handlers = [handler]
logger.propagate = False

# Configuration
AGENT_POLL_INTERVAL = int(os.getenv("AGENT_POLL_INTERVAL", "30"))  # seconds


async def discover_and_refresh_agents(app: FastAPI, is_startup: bool = False) -> Dict[str, Any]:
    """Discover agents and refresh proxy configuration"""

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Check for AWS credentials and warn if missing
    if not aws_access_key_id or not aws_secret_access_key:
        logger.warning("Unable to access AgentCore - ensure your AWS credential chain is configured - see README")
        app.state.client = None
        app.state.agents = []
        # Still create a basic proxy for the routes on startup
        if is_startup:
            app.state.proxy = A2AProxy(None)
            if not hasattr(app.state, "a2a_routes_added"):
                app.include_router(app.state.proxy.get_router())
                app.state.a2a_routes_added = True
        return {
            "message": "No AWS credentials configured",
            "agents_discovered": 0,
            "region": aws_region,
            "agents": [],
        }

    # Use existing client if available, otherwise create new one
    if hasattr(app.state, "client"):
        client = app.state.client
    else:
        try:
            client = AgentCoreClient(
                access_key_id=aws_access_key_id, secret_access_key=aws_secret_access_key, region=aws_region
            )
            app.state.client = client
        except Exception as e:
            if is_startup:
                logger.error(f"AWS connection failed during startup: {e}")
                logger.info("Server will start without AWS connectivity - check credentials and network access")
                app.state.client = None
                app.state.agents = []
                # Still create a basic proxy for the routes
                app.state.proxy = A2AProxy(None)
                if not hasattr(app.state, "a2a_routes_added"):
                    app.include_router(app.state.proxy.get_router())
                    app.state.a2a_routes_added = True
                return {
                    "message": "Server started without AWS connectivity",
                    "agents_discovered": 0,
                    "region": aws_region,
                    "agents": [],
                    "error": str(e)
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
                "error": str(e)
            }

    # Clear existing agents and reinitialize
    if hasattr(app.state, "proxy"):
        proxy = app.state.proxy
        # Clear existing agents from proxy
        proxy.agents.clear()
        proxy.a2a_apps.clear()
    else:
        proxy = A2AProxy(client)
        app.state.proxy = proxy
        # Include A2A routes on first setup
        if not hasattr(app.state, "a2a_routes_added"):
            app.include_router(proxy.get_router())
            app.state.a2a_routes_added = True

    # Initialize agents in proxy
    await proxy.initialize_agents(agents)
    app.state.agents = agents

    # Show polling result in one line
    if agents:
        agent_names = [agent.get("agentRuntimeName", f"agent-{agent.get('agentRuntimeId')}") for agent in agents]
        # Format agent names in bright white
        formatted_names = [f"\033[1;37m{name}\033[0m" for name in agent_names]
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
            await asyncio.sleep(AGENT_POLL_INTERVAL)
            await discover_and_refresh_agents(app, is_startup=False)
        except Exception as e:
            logger.error(f"error during agent polling: {e}")
            # Continue polling even if one iteration fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clean splash message with INFO style
    print("\033[32mINFO\033[0m:     \033[1;37mAWS Bedrock AgentCore A2A Proxy\033[0m")
    print("\033[32mINFO\033[0m:     API Server:  \033[34mhttp://localhost:2972\033[0m")
    print("\033[32mINFO\033[0m:     API Docs:    \033[34mhttp://localhost:2972/docs\033[0m")

    # Initial agent discovery
    await discover_and_refresh_agents(app, is_startup=True)

    # Start background polling task
    polling_task = asyncio.create_task(agent_polling_task(app))
    app.state.polling_task = polling_task

    yield

    # Cancel polling task
    if hasattr(app.state, "polling_task"):
        app.state.polling_task.cancel()
        try:
            await app.state.polling_task
        except asyncio.CancelledError:
            pass

    # Shutdown the A2A proxy
    if hasattr(app.state, "proxy"):
        await app.state.proxy.shutdown()


app = FastAPI(
    title="AWS Bedrock AgentCore A2A Server",
    description="Creates A2A proxy servers for each AWS Bedrock AgentCore agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "AWS Bedrock AgentCore A2A Server is running"}


@app.get("/status")
async def status():
    """Get server status"""
    agents = getattr(app.state, 'agents', [])
    proxy = getattr(app.state, 'proxy', None)
    running_servers = 0

    if proxy and hasattr(proxy, 'running_servers'):
        running_servers = len(proxy.running_servers)
    return {
        "agents_discovered": len(agents),
        "a2a_servers_running": running_servers,
        "agents": [{"agent_id": agent.get("agentId", "")} for agent in agents]
    }


@app.get("/agents")
async def list_agents():
    """List all discovered agents"""
    return getattr(app.state, 'agents', [])


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    """Check if server can connect to AWS"""
    try:
        if not hasattr(app.state, "client"):
            raise HTTPException(status_code=503, detail="AWS client not initialized")

        # Test AWS connectivity by listing agents
        agents = await app.state.client.list_agents()
        return {"status": "ready", "aws_connection": "ok", "agents_available": len(agents)}
    except Exception as e:
        logger.error(f"AWS connectivity check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")
