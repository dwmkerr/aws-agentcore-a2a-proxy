import logging
import uuid
import json
from typing import Dict, List, Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from .aws_a2a_translation import (
    agentcore_agent_to_agentcard,
    a2a_request_to_agentcore_payload,
    agentcore_response_to_a2a_message,
    agentcore_streaming_to_a2a_chunks,
)

logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="AWS Bedrock AgentCore A2A Server",
    description="Creates A2A proxy servers for each AWS Bedrock AgentCore agent",
)


@app.get("/")
async def root():
    return {"message": "AWS Bedrock AgentCore A2A Server is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/status")
async def status():
    """Get server status"""
    return {
        "agents_discovered": len(app.state.agents),
        "agents": [{"agent_id": agent_id} for agent_id in app.state.agents.keys()],
    }


@app.get("/ready")
async def ready():
    """Check if server can connect to AWS"""
    try:
        # Test AWS connectivity by listing agents
        agents = await app.state.client.list_agents()
        return {"status": "ready", "aws_connection": "ok", "agents_available": len(agents)}
    except Exception as e:
        logger.error(f"AWS connectivity check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")


@app.get("/a2a/agents")
async def list_a2a_agents():
    """A2A agents list endpoint with full Agent Cards"""
    base_url = app.state.config.get_base_url()
    return [
        agentcore_agent_to_agentcard(
            agent_id,
            agent_data,
            base_url=base_url,
            streaming_enabled=app.state.config.enable_streaming,
            description_as_skill=app.state.config.enable_description_as_a2a_skill,
        )
        for agent_id, agent_data in app.state.agents.items()
    ]


@app.get("/a2a/agent/{agent_id}/.well-known/agent.json")
async def get_agent_card_wellknown(agent_id: str):
    """A2A standard agent card discovery endpoint"""
    if agent_id not in app.state.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    base_url = app.state.config.get_base_url()
    agent = app.state.agents[agent_id]
    return agentcore_agent_to_agentcard(
        agent_id,
        agent,
        base_url=base_url,
        streaming_enabled=app.state.config.enable_streaming,
        description_as_skill=app.state.config.enable_description_as_a2a_skill,
    )


@app.post("/a2a/agent/{agent_id}")
async def handle_a2a_agent_messages(agent_id: str, request: Request):
    """Handle A2A agent message requests"""

    if agent_id not in app.state.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Parse JSON body
    try:
        request_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Check if this is a streaming request
    if isinstance(request_data, dict) and request_data.get("method") == "message/stream":
        # Handle streaming A2A request
        return await _handle_a2a_streaming(agent_id, request_data)
    else:
        # Handle regular A2A request
        return await _handle_a2a_regular(agent_id, request_data)


@app.get("/agentcore/agents")
async def list_agentcore_agents():
    """AgentCore raw agents list endpoint"""
    return [
        {
            "agentRuntimeId": agent_id,
            "agentRuntimeName": agent.get("agentRuntimeName"),
            "agentRuntimeArn": agent.get("agentRuntimeArn"),
            "description": agent.get("description"),
            "status": agent.get("status"),
            "version": agent.get("agentRuntimeVersion"),
            "lastUpdatedAt": agent.get("lastUpdatedAt"),
        }
        for agent_id, agent in app.state.agents.items()
    ]


@app.post("/agentcore/agents/{agent_id}/invoke")
async def invoke_agentcore_agent(agent_id: str, payload: Dict[str, Any]):
    """Direct AgentCore invocation endpoint (bypasses A2A protocol)"""
    if agent_id not in app.state.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        # Call AgentCore directly
        raw_result = await app.state.client.invoke_agent(agent_id, payload)
        return raw_result
    except Exception as e:
        logger.error(f"Failed to invoke AgentCore agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agentcore/agents/{agent_id}/invoke-stream")
async def invoke_agentcore_agent_stream(agent_id: str, payload: Dict[str, Any]):
    """Direct AgentCore streaming invocation endpoint"""
    if agent_id not in app.state.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    async def stream_generator():
        try:
            prompt = payload.get("prompt", "")
            # Use unified AgentCore client with streaming=True flag
            response = await app.state.client.invoke_agent(agent_id, {"prompt": prompt}, streaming=True)

            if response.get("streaming", False):
                # Handle streaming response
                response_iterator = response["response"]
                for line in response_iterator.iter_lines(chunk_size=10):
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            line = line[6:]  # Remove 'data: ' prefix
                        if line == "[DONE]":
                            break
                        yield f"data: {line}\n\n"
            else:
                # Handle single response as one chunk
                chunk_json = json.dumps(response)
                yield f"data: {chunk_json}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Failed to stream AgentCore agent {agent_id}: {e}")
            error_json = json.dumps({"error": str(e)})
            yield f"data: {error_json}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _handle_a2a_regular(agent_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle regular (non-streaming) A2A requests"""
    try:
        # Translate A2A request to AgentCore payload
        payload = a2a_request_to_agentcore_payload(request_data)

        # Call AgentCore
        agentcore_response = await app.state.client.invoke_agent(agent_id, payload)

        # Translate AgentCore response to A2A message
        return agentcore_response_to_a2a_message(agentcore_response, request_data.get("id"))

    except ValueError as e:
        # Translation error - bad request
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling A2A request for agent {agent_id}: {e}")
        return {"error": f"Agent execution failed: {str(e)}"}


async def _handle_a2a_streaming(agent_id: str, request_data: Dict[str, Any]) -> StreamingResponse:
    """Handle streaming A2A requests"""
    try:
        # Translate A2A request to AgentCore payload
        payload = a2a_request_to_agentcore_payload(request_data)

        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                # Call AgentCore
                agentcore_response = await app.state.client.invoke_agent(agent_id, payload)

                # Translate AgentCore response to A2A chunks
                for chunk in agentcore_streaming_to_a2a_chunks(agentcore_response, request_data.get("id")):
                    yield chunk

            except Exception as e:
                # Send A2A-formatted error
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id", str(uuid.uuid4())),
                    "error": {"message": f"Agent execution failed: {str(e)}"},
                }
                yield f"data: {json.dumps(error_response)}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except ValueError as e:
        # Translation error - bad request
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling A2A streaming request for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def refresh_agents() -> List[Dict[str, Any]]:
    """Discover and refresh agents"""
    agents = await app.state.client.list_agents()
    app.state.agents.clear()
    await initialize_agents(agents)

    # Call callback if provided. A bit like a HTTP server request handler or
    # middleware, if it throws then we'll log an error but not terminate the
    # process.
    if hasattr(app.state, "on_agents_refresh") and app.state.on_agents_refresh:
        try:
            await app.state.on_agents_refresh(agents)
        except Exception as e:
            logger.error(f"Error on agent refresh handler: {e}")

    return agents


async def initialize_agents(agents: List[Dict[str, Any]]) -> None:
    logger.info(f"Registering {len(agents)} agents for A2A proxy")

    for agent in agents:
        agent_id = agent.get("agentRuntimeId")
        if agent_id:
            app.state.agents[agent_id] = agent
            logger.info(f"Registered agent {agent_id} -> /a2a/agent/{agent_id} (A2A JSON-RPC 2.0)")

    logger.info(f"Successfully registered {len(app.state.agents)} agents for A2A access")


def get_agent_addresses() -> List[Dict[str, str]]:
    """Get list of A2A addresses for all agents"""
    base_url = app.state.config.get_base_url()
    return [
        {
            "agent_id": agent_id,
            "agent_name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
            "a2a_address": f"{base_url}/a2a/agent/{agent_id}",
            "status": agent.get("status", "unknown"),
        }
        for agent_id, agent in app.state.agents.items()
    ]
