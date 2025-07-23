import os
import logging
from typing import Dict, List, Any
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from .agentcore_client import AgentCoreClient
from .a2a_proxy import A2AProxy

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    status: str
    arn: str


class ServerStatus(BaseModel):
    agents_discovered: int
    a2a_servers_running: int
    agents: List[AgentInfo]


async def initialize_agents(app: FastAPI) -> Dict[str, Any]:
    """Initialize AWS client and discover agents"""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    logger.info(f"Using AWS region: {aws_region}")
    
    # Use explicit credentials if provided, otherwise fall back to default credential chain
    if aws_access_key_id and aws_secret_access_key:
        logger.info("Using explicit AWS credentials from environment variables")
        client = AgentCoreClient(
            access_key_id=aws_access_key_id,
            secret_access_key=aws_secret_access_key,
            region=aws_region
        )
    else:
        logger.info("Using default AWS credential chain (AWS CLI, IAM roles, etc.)")
        # Pass empty strings to trigger default credential chain usage
        client = AgentCoreClient(
            access_key_id="",
            secret_access_key="",
            region=aws_region
        )
    
    agents = await client.list_agents()
    logger.info(f"Discovered {len(agents)} AgentCore agents")
    
    proxy = A2AProxy(client)
    await proxy.initialize_agents(agents)
    
    # Store in app state
    app.state.client = client
    app.state.proxy = proxy
    app.state.agents = agents
    
    # Include A2A routes if not already included
    if not hasattr(app.state, 'a2a_routes_added'):
        app.include_router(proxy.get_router())
        app.state.a2a_routes_added = True
    
    # Log discovery info with correct A2A endpoints
    logger.info("=" * 60)
    logger.info(f"🤖 Discovered {len(agents)} AgentCore agents")
    logger.info("🔗 A2A Endpoints available:")
    for agent in agents:
        agent_id = agent.get('agentRuntimeId')
        agent_name = agent.get('agentRuntimeName', f'agent-{agent_id}')
        logger.info(f"   • {agent_name}:")
        logger.info(f"     Agent Card: \033[34mhttp://localhost:2972/a2a/agent/{agent_id}/.well-known/agent.json\033[0m")
        logger.info(f"     JSON-RPC:   \033[34mhttp://localhost:2972/a2a/agent/{agent_id}/jsonrpc\033[0m")
    logger.info("📋 AgentCore endpoints:")
    logger.info(f"   List agents:   \033[34mhttp://localhost:2972/agentcore/agents\033[0m")
    logger.info(f"   A2A agents:    \033[34mhttp://localhost:2972/a2a/agents\033[0m")
    logger.info("=" * 60)
    
    return {
        "message": "Agent discovery completed",
        "agents_discovered": len(agents),
        "region": aws_region,
        "agents": agents
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AWS Bedrock AgentCore A2A Server")
    logger.info("=" * 60)
    logger.info("\033[1;37mAWS Bedrock AgentCore A2A Server Started!\033[0m")
    logger.info("=" * 60)
    logger.info(f"API Server:     \033[34mhttp://localhost:2972\033[0m")
    logger.info(f"API Docs:       \033[34mhttp://localhost:2972/docs\033[0m")
    logger.info(f"Redoc:          \033[34mhttp://localhost:2972/redoc\033[0m")
    logger.info(f"Status:         \033[34mhttp://localhost:2972/status\033[0m")
    logger.info(f"A2A Addresses:  \033[34mhttp://localhost:2972/a2a-addresses\033[0m")
    logger.info(f"Discover:       \033[34mhttp://localhost:2972/rpc/discover\033[0m")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down A2A servers")
    
    # Shutdown the A2A proxy
    if hasattr(app.state, 'proxy'):
        await app.state.proxy.shutdown()


app = FastAPI(
    title="AWS Bedrock AgentCore A2A Server",
    description="Creates A2A proxy servers for each AWS Bedrock AgentCore agent",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {"message": "AWS Bedrock AgentCore A2A Server is running"}


@app.post("/rpc/discover")
async def discover():
    """Discover AWS AgentCore agents"""
    try:
        result = await initialize_agents(app)
        return result
    except Exception as e:
        logger.error(f"Failed to discover agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=ServerStatus)
async def get_status():
    if not hasattr(app.state, 'agents'):
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    agents_info = [
        AgentInfo(
            agent_id=agent["agentId"],
            name=agent.get("agentName", ""),
            status=agent.get("status", "unknown"),
            arn=agent.get("agentArn", "")
        )
        for agent in app.state.agents
    ]
    
    return ServerStatus(
        agents_discovered=len(app.state.agents),
        a2a_servers_running=len(app.state.proxy.agents) if hasattr(app.state, 'proxy') else 0,
        agents=agents_info
    )


@app.get("/agents")
async def list_agents():
    if not hasattr(app.state, 'agents'):
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    return app.state.agents


@app.get("/a2a-addresses")
async def get_a2a_addresses():
    if not hasattr(app.state, 'proxy'):
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    return {
        "message": "A2A addresses for AgentCore agents",
        "base_url": "localhost:2972",
        "agents": app.state.proxy.get_agent_addresses()
    }


@app.post("/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, payload: Dict[str, Any]):
    if not hasattr(app.state, 'proxy'):
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        result = await app.state.proxy.invoke_agent(agent_id, payload)
        return result
    except Exception as e:
        logger.error(f"Failed to invoke agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("aws_bedrock_a2a_proxy.main:app", host="0.0.0.0", port=2972, reload=True)