import logging
import uuid
import json
from typing import Dict, List, Any, AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .agentcore_client import AgentCoreClient
from .aws_a2a_translation import (
    agentcore_agent_to_agentcard,
    a2a_request_to_agentcore_payload,
    agentcore_response_to_a2a_message,
    agentcore_streaming_to_a2a_chunks,
)

logger = logging.getLogger(__name__)


class A2AProxy:
    def __init__(self, agentcore_client: Optional[AgentCoreClient] = None):
        self.client = agentcore_client
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.a2a_router = APIRouter()
        self.setup_a2a_routes()

    def setup_a2a_routes(self):
        """Set up A2A routing endpoints"""

        @self.a2a_router.get("/a2a/agents")
        async def list_a2a_agents():
            """A2A agents list endpoint with full Agent Cards"""
            from .main import ENABLE_STREAMING, ENABLE_DESCRIPTION_AS_A2A_SKILL, EXPOSE_HOST, EXPOSE_PORT, BASE_PATH

            base_url = f"http://{EXPOSE_HOST}:{EXPOSE_PORT}{BASE_PATH}"
            return [
                agentcore_agent_to_agentcard(
                    agent_id,
                    agent_data,
                    base_url=base_url,
                    streaming_enabled=ENABLE_STREAMING,
                    description_as_skill=ENABLE_DESCRIPTION_AS_A2A_SKILL,
                )
                for agent_id, agent_data in self.agents.items()
            ]

        @self.a2a_router.get("/a2a/agent/{agent_id}/.well-known/agent.json")
        async def get_agent_card_wellknown(agent_id: str):
            """A2A standard agent card discovery endpoint"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            from .main import ENABLE_STREAMING, ENABLE_DESCRIPTION_AS_A2A_SKILL, EXPOSE_HOST, EXPOSE_PORT, BASE_PATH

            base_url = f"http://{EXPOSE_HOST}:{EXPOSE_PORT}{BASE_PATH}"
            agent = self.agents[agent_id]
            return agentcore_agent_to_agentcard(
                agent_id,
                agent,
                base_url=base_url,
                streaming_enabled=ENABLE_STREAMING,
                description_as_skill=ENABLE_DESCRIPTION_AS_A2A_SKILL,
            )

        @self.a2a_router.post("/a2a/agent/{agent_id}")
        async def handle_a2a_agent_messages(agent_id: str, request: Request):
            """Handle A2A agent message requests"""

            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            # Parse JSON body
            try:
                request_data = await request.json()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

            # Check if this is a streaming request
            if isinstance(request_data, dict) and request_data.get("method") == "message/stream":
                # Handle streaming A2A request
                return await self._handle_a2a_streaming(agent_id, request_data)
            else:
                # Handle regular A2A request
                return await self._handle_a2a_regular(agent_id, request_data)

        @self.a2a_router.get("/agentcore/agents")
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
                for agent_id, agent in self.agents.items()
            ]

        @self.a2a_router.post("/agentcore/agents/{agent_id}/invoke")
        async def invoke_agentcore_agent(agent_id: str, payload: Dict[str, Any]):
            """Direct AgentCore invocation endpoint (bypasses A2A protocol)"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            if self.client is None:
                raise HTTPException(status_code=503, detail="AgentCore client not initialized")

            try:
                # Call AgentCore directly
                raw_result = await self.client.invoke_agent(agent_id, payload)
                return raw_result
            except Exception as e:
                logger.error(f"Failed to invoke AgentCore agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.a2a_router.post("/agentcore/agents/{agent_id}/invoke-stream")
        async def invoke_agentcore_agent_stream(agent_id: str, payload: Dict[str, Any]):
            """Direct AgentCore streaming invocation endpoint"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            from fastapi.responses import StreamingResponse
            import json

            async def stream_generator():
                try:
                    if self.client is None:
                        error_json = json.dumps({"error": "AgentCore client not initialized"})
                        yield f"data: {error_json}\n\n"
                        return

                    prompt = payload.get("prompt", "")
                    # Use unified AgentCore client with streaming=True flag
                    response = await self.client.invoke_agent(agent_id, {"prompt": prompt}, streaming=True)

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

    async def _handle_a2a_regular(self, agent_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regular (non-streaming) A2A requests"""
        try:
            # Translate A2A request to AgentCore payload
            payload = a2a_request_to_agentcore_payload(request_data)

            if self.client is None:
                raise HTTPException(status_code=503, detail="AgentCore client not initialized")

            # Call AgentCore
            agentcore_response = await self.client.invoke_agent(agent_id, payload)

            # Translate AgentCore response to A2A message
            return agentcore_response_to_a2a_message(agentcore_response, request_data.get("id"))

        except ValueError as e:
            # Translation error - bad request
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error handling A2A request for agent {agent_id}: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}

    async def _handle_a2a_streaming(self, agent_id: str, request_data: Dict[str, Any]) -> StreamingResponse:
        """Handle streaming A2A requests"""
        try:
            # Translate A2A request to AgentCore payload
            payload = a2a_request_to_agentcore_payload(request_data)

            async def stream_generator() -> AsyncGenerator[str, None]:
                try:
                    if self.client is None:
                        # Send A2A-formatted error
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_data.get("id", str(uuid.uuid4())),
                            "error": {"message": "AgentCore client not initialized"},
                        }
                        yield f"data: {json.dumps(error_response)}\n\n"
                        return

                    # Call AgentCore
                    agentcore_response = await self.client.invoke_agent(agent_id, payload)

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

    async def initialize_agents(self, agents: List[Dict[str, Any]]) -> None:
        logger.info(f"Registering {len(agents)} agents for A2A proxy")

        for agent in agents:
            agent_id = agent.get("agentRuntimeId")
            if agent_id:
                self.agents[agent_id] = agent
                logger.info(f"Registered agent {agent_id} -> /a2a/agent/{agent_id} (A2A JSON-RPC 2.0)")

        logger.info(f"Successfully registered {len(self.agents)} agents for A2A access")

    def get_router(self) -> APIRouter:
        """Get the FastAPI router for A2A endpoints"""
        return self.a2a_router

    async def invoke_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        if self.client is None:
            raise ValueError("AgentCore client not initialized")

        try:
            # Return raw AgentCore response - endpoints handle their own translation
            result = await self.client.invoke_agent(agent_id, payload)
            return result

        except Exception as e:
            logger.error(f"Failed to invoke agent {agent_id}: {e}")
            raise

    async def shutdown(self) -> None:
        logger.info("Shutting down A2A proxy")
        self.agents.clear()
        logger.info("A2A proxy shutdown complete")

    def get_agent_addresses(self) -> List[Dict[str, str]]:
        """Get list of A2A addresses for all agents"""
        from .main import EXPOSE_HOST, EXPOSE_PORT, BASE_PATH

        base_url = f"http://{EXPOSE_HOST}:{EXPOSE_PORT}{BASE_PATH}"
        return [
            {
                "agent_id": agent_id,
                "agent_name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
                "a2a_address": f"{base_url}/a2a/agent/{agent_id}",
                "status": agent.get("status", "unknown"),
            }
            for agent_id, agent in self.agents.items()
        ]
