import logging
import uuid
from typing import Dict, List, Any

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TextPart
from fastapi import APIRouter, HTTPException, Request

from .agentcore_client import AgentCoreClient
from .agentcore_streaming_invocation_client import AgentCoreStreamingInvocationClient
from .agentcore_executor import AgentCoreExecutor
from .aws_a2a_translation import agentcore_agent_to_agentcard

logger = logging.getLogger(__name__)


class A2AProxy:
    def __init__(self, agentcore_client: AgentCoreClient = None):
        self.client = agentcore_client
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.a2a_apps: Dict[str, A2AStarletteApplication] = {}
        self.a2a_router = APIRouter()
        self.setup_a2a_routes()


    def setup_a2a_routes(self):
        """Set up A2A routing endpoints"""

        @self.a2a_router.get("/a2a/agents")
        async def list_a2a_agents():
            """A2A agents list endpoint with full Agent Cards"""
            return [
                agentcore_agent_to_agentcard(agent_id, agent_data)
                for agent_id, agent_data in self.agents.items()
            ]

        @self.a2a_router.get("/a2a/agent/{agent_id}/.well-known/agent.json")
        async def get_agent_card(agent_id: str):
            """Agent card endpoint per A2A standard"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            return agentcore_agent_to_agentcard(agent_id, agent)

        @self.a2a_router.post("/a2a/agent/{agent_id}")
        async def handle_a2a_agent_request(agent_id: str, request: Dict[str, Any]):
            """Main A2A agent endpoint - routes to appropriate agent"""
            
            if agent_id not in self.a2a_apps:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            
            # Get the A2A app for this agent and delegate the request
            a2a_app = self.a2a_apps[agent_id]
            
            # The A2A SDK app will handle the request properly
            # We need to create a proper ASGI scope and call the app
            from starlette.requests import Request
            from starlette.responses import JSONResponse
            
            try:
                # Extract message from A2A standard JSON-RPC format only
                message_text = ""
                
                # A2A standard: JSON-RPC with params.message.parts[0].text
                if isinstance(request, dict) and "params" in request:
                    params = request["params"]
                    if "message" in params and "parts" in params["message"]:
                        parts = params["message"]["parts"]
                        if parts and len(parts) > 0 and "text" in parts[0]:
                            message_text = parts[0]["text"]
                
                # No fallback - only A2A standard format supported
                if not message_text:
                    raise HTTPException(status_code=400, detail="Invalid A2A request: missing params.message.parts[0].text")
                
                # Call AgentCore directly
                payload = {"prompt": message_text}
                raw_result = await self.client.invoke_agent(agent_id, payload)
                
                # Extract response text from AgentCore format
                if isinstance(raw_result, dict) and "result" in raw_result and "content" in raw_result["result"]:
                    text_parts = []
                    for content_item in raw_result["result"]["content"]:
                        if isinstance(content_item, dict) and "text" in content_item:
                            text_parts.append(content_item["text"])
                    response_text = "".join(text_parts).strip()
                else:
                    response_text = str(raw_result)
                
                # Create A2A Message using SDK types
                response_message = Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text=response_text)]
                )
                
                # Return JSON-RPC success response with proper A2A Message object
                return {"result": response_message.model_dump()}
                
            except Exception as e:
                logger.error(f"Error handling A2A request for agent {agent_id}: {e}")
                # Return JSON-RPC error response format expected by A2A inspector
                return {"error": f"Agent execution failed: {str(e)}"}


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
                    prompt = payload.get("prompt", "")
                    # Create streaming client for streaming
                    streaming_client = AgentCoreStreamingInvocationClient(region="us-east-1")

                    async for chunk in streaming_client.invoke_agent_stream(agent_id, prompt):
                        # Send each chunk as Server-Sent Event
                        chunk_json = json.dumps(chunk)
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

    async def initialize_agents(self, agents: List[Dict[str, Any]]) -> None:
        logger.info(f"Registering {len(agents)} agents for A2A proxy")

        for agent in agents:
            agent_id = agent.get("agentRuntimeId")
            if agent_id:
                self.agents[agent_id] = agent

                # Create A2A application for this agent
                agent_name = agent.get("agentRuntimeName", f"agent-{agent_id}")

                # Create agent card
                agent_card = AgentCard(
                    name=agent_name,
                    description=agent.get("description", "AWS Bedrock AgentCore agent"),
                    url=f"http://localhost:2972/a2a/agent/{agent_id}",
                    version=agent.get("agentRuntimeVersion", "1"),
                    default_input_modes=["text/plain"],
                    default_output_modes=["text/plain"],
                    capabilities=AgentCapabilities(
                        streaming=True, push_notifications=False, state_transition_history=False
                    ),
                    skills=[
                        AgentSkill(
                            id="customer_support",
                            name="Customer Support",
                            description="Handle customer inquiries and support requests",
                            tags=["support", "customer", "help"],
                        ),
                        AgentSkill(
                            id="order_tracking",
                            name="Order Tracking",
                            description="Track and look up customer orders",
                            tags=["orders", "tracking", "status"],
                        ),
                        AgentSkill(
                            id="knowledge_base",
                            name="Knowledge Base",
                            description="Query product knowledge and documentation",
                            tags=["knowledge", "documentation", "info"],
                        ),
                    ],
                )

                # Create streaming client for this agent
                streaming_client = AgentCoreStreamingInvocationClient(region="us-east-1")

                # Create agent executor
                executor = AgentCoreExecutor(self.client, streaming_client, agent_id)

                # Create request handler
                handler = DefaultRequestHandler(
                    agent_executor=executor,
                    task_store=InMemoryTaskStore(),
                )

                # Create A2A application
                a2a_app = A2AStarletteApplication(
                    agent_card=agent_card,
                    http_handler=handler,
                )

                self.a2a_apps[agent_id] = a2a_app

                logger.info(f"Registered agent {agent_id} -> /a2a/agent/{agent_id} (A2A JSON-RPC 2.0)")

        logger.info(f"Successfully registered {len(self.agents)} agents for A2A access")

    def get_router(self) -> APIRouter:
        """Get the FastAPI router for A2A endpoints"""
        return self.a2a_router
    
    def get_a2a_apps(self) -> Dict[str, Any]:
        """Get the A2A applications that need to be mounted"""
        return self.a2a_apps

    async def invoke_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

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
        self.a2a_apps.clear()
        logger.info("A2A proxy shutdown complete")

    def get_agent_addresses(self) -> List[Dict[str, str]]:
        """Get list of A2A addresses for all agents"""
        return [
            {
                "agent_id": agent_id,
                "agent_name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
                "a2a_address": f"localhost:2972/a2a/agent/{agent_id}",
                "status": agent.get("status", "unknown"),
            }
            for agent_id, agent in self.agents.items()
        ]
