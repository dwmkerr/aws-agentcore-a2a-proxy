import logging
import uuid
from typing import Dict, List, Any

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TextPart
from fastapi import APIRouter, HTTPException

from .agentcore_client import AgentCoreClient
from .agentcore_http_client import AgentCoreHTTPClient

logger = logging.getLogger(__name__)


class AgentCoreExecutor:
    """Agent executor that bridges A2A requests to AWS Bedrock AgentCore agents"""

    def __init__(self, http_client: AgentCoreHTTPClient, agent_id: str):
        self.http_client = http_client
        self.agent_id = agent_id

    async def execute(self, context: Any, event_queue: Any) -> None:
        """Execute agent request and stream response back"""
        try:
            # Extract message text from A2A context
            message_text = ""
            if context.message and context.message.parts:
                first_part = context.message.parts[0]
                if hasattr(first_part, "root") and hasattr(first_part.root, "text"):
                    message_text = first_part.root.text

            logger.info(f"Executing agent {self.agent_id} with message: {message_text[:100]}...")

            # Check if streaming is requested (look for streaming capability in context)
            should_stream = self._should_use_streaming(context)

            if should_stream:
                await self._execute_streaming(context, event_queue, message_text)
            else:
                await self._execute_single_response(context, event_queue, message_text)

        except Exception as e:
            logger.error(f"Failed to execute agent {self.agent_id}: {e}")
            # Send error response
            error_message = Message(
                message_id=str(uuid.uuid4()),
                context_id=(
                    context.message.context_id if context.message and context.message.context_id else str(uuid.uuid4())
                ),
                task_id=context.task_id,
                role=Role.agent,
                parts=[Part(root=TextPart(kind="text", text=f"Error: {str(e)}"))],
            )
            await event_queue.enqueue_event(error_message)

    def _should_use_streaming(self, context: Any) -> bool:
        """Determine if streaming should be used based on context"""
        # Check if streaming is explicitly requested in the context
        # This could be via headers, task preferences, or agent capabilities
        if hasattr(context, "preferences") and context.preferences:
            return context.preferences.get("streaming", False)

        # For now, we'll default to non-streaming to maintain compatibility
        # In the future, this could be configurable or auto-detected
        return False

    async def _execute_streaming(self, context: Any, event_queue: Any, message_text: str) -> None:
        """Execute with streaming response"""
        logger.info(f"Using streaming execution for agent {self.agent_id}")

        try:
            # Stream response from AgentCore
            async for chunk in self.http_client.invoke_agent_stream(self.agent_id, message_text):
                # Extract text from chunk
                chunk_text = self._extract_chunk_text(chunk)

                if chunk_text:
                    # Create streaming message
                    stream_message = Message(
                        message_id=str(uuid.uuid4()),
                        context_id=(
                            context.message.context_id
                            if context.message and context.message.context_id
                            else str(uuid.uuid4())
                        ),
                        task_id=context.task_id,
                        role=Role.agent,
                        parts=[Part(root=TextPart(kind="text", text=chunk_text))],
                    )

                    # Send chunk via event queue
                    await event_queue.enqueue_event(stream_message)
                    logger.debug(f"Sent streaming chunk: {chunk_text[:50]}...")

            logger.info(f"Streaming execution completed for agent {self.agent_id}")

        except Exception as e:
            logger.error(f"Streaming execution failed for agent {self.agent_id}: {e}")
            raise

    async def _execute_single_response(self, context: Any, event_queue: Any, message_text: str) -> None:
        """Execute with single response (original behavior)"""
        # Call AgentCore agent via HTTP client
        result = await self.http_client.invoke_agent(self.agent_id, message_text)

        # Extract response text from AgentCore format
        if isinstance(result, dict) and "result" in result and "content" in result["result"]:
            text_parts = []
            for content_item in result["result"]["content"]:
                if isinstance(content_item, dict) and "text" in content_item:
                    text_parts.append(content_item["text"])
            response_text = "".join(text_parts).strip()
        else:
            response_text = str(result)

        # Create A2A response message
        response_message = Message(
            message_id=str(uuid.uuid4()),
            context_id=(
                context.message.context_id if context.message and context.message.context_id else str(uuid.uuid4())
            ),
            task_id=context.task_id,
            role=Role.agent,
            parts=[Part(root=TextPart(kind="text", text=response_text))],
        )

        # Send response back via event queue
        await event_queue.enqueue_event(response_message)

        logger.info(f"Agent {self.agent_id} execution completed")

    def _extract_chunk_text(self, chunk: Dict[str, Any]) -> str:
        """Extract text content from streaming chunk"""
        if isinstance(chunk, dict):
            # Handle various chunk formats
            if "text" in chunk:
                return chunk["text"]
            elif "result" in chunk and isinstance(chunk["result"], dict):
                if "content" in chunk["result"]:
                    # Similar to single response format
                    content = chunk["result"]["content"]
                    if isinstance(content, list) and content:
                        first_item = content[0]
                        if isinstance(first_item, dict) and "text" in first_item:
                            return first_item["text"]
                elif "text" in chunk["result"]:
                    return chunk["result"]["text"]
            elif "delta" in chunk and isinstance(chunk["delta"], dict):
                # Handle delta-style streaming
                if "text" in chunk["delta"]:
                    return chunk["delta"]["text"]

        return str(chunk) if chunk else ""

    async def cancel(self, context: Any, event_queue: Any) -> None:
        """Cancel agent execution (not implemented for AgentCore)"""
        logger.info(f"Cancel requested for agent {self.agent_id}")
        pass


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
            """A2A agents list endpoint with agent cards"""
            return [
                {
                    "agent_id": agent_id,
                    "name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
                    "description": agent.get("description", "AgentCore agent"),
                    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
                    "host": "localhost:2972",
                    "agent_card": f"/a2a/agent/{agent_id}/.well-known/agent.json",
                    "agent_url": f"http://localhost:2972/a2a/agent/{agent_id}",
                    "endpoint": f"/a2a/agent/{agent_id}",
                    "status": agent.get("status", "unknown"),
                    "metadata": {
                        "type": "bedrock-agentcore",
                        "version": agent.get("agentRuntimeVersion", "1"),
                        "agent_id": agent_id,
                    },
                }
                for agent_id, agent in self.agents.items()
            ]

        @self.a2a_router.get("/a2a/agent/{agent_id}/.well-known/agent.json")
        async def get_agent_card(agent_id: str):
            """Agent card endpoint per A2A standard"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            agent_name = agent.get("agentRuntimeName", f"agent-{agent_id}")
            
            # Generate agent-specific description and skills using A2A SDK
            if "aws_operator" in agent_name:
                description = "General-purpose AWS operations assistant with boto3 integration"
                skills = [
                    AgentSkill(
                        id="execute_aws_operation",
                        name="execute_aws_operation", 
                        description="Execute any AWS operation via boto3 using natural language",
                        tags=["aws", "boto3", "infrastructure"]
                    ),
                    AgentSkill(
                        id="list_aws_resources",
                        name="list_aws_resources",
                        description="List resources across AWS services (S3, EC2, Lambda, etc.)",
                        tags=["aws", "resources", "list"]
                    ),
                    AgentSkill(
                        id="get_aws_identity", 
                        name="get_aws_identity",
                        description="Get current AWS caller identity and permissions",
                        tags=["aws", "identity", "sts"]
                    ),
                ]
            elif "github_dev" in agent_name:
                description = "GitHub development assistant with OIDC integration and MCP server access"
                skills = [
                    AgentSkill(
                        id="manage_pull_requests",
                        name="manage_pull_requests",
                        description="View and manage GitHub pull requests", 
                        tags=["github", "pr", "development"]
                    ),
                    AgentSkill(
                        id="handle_issues",
                        name="handle_issues", 
                        description="Create and manage GitHub issues",
                        tags=["github", "issues", "development"]
                    ),
                    AgentSkill(
                        id="access_repositories",
                        name="access_repositories",
                        description="Access and analyze GitHub repositories",
                        tags=["github", "repository", "analysis"]
                    ),
                ]
            else:
                # Fallback for other agents
                description = agent.get("description", "AgentCore agent")
                skills = [
                    AgentSkill(
                        id="general_assistance",
                        name="general_assistance",
                        description="Provide general assistance based on agent capabilities",
                        tags=["general", "assistance"]
                    ),
                ]
            
            # Create agent card using A2A SDK
            agent_url = f"http://localhost:2972/a2a/agent/{agent_id}"
            agent_card = AgentCard(
                name=agent_name,
                description=description,
                url=agent_url,
                default_input_modes=["text"],
                default_output_modes=["text"],
                capabilities=AgentCapabilities(
                    streaming=False, 
                    push_notifications=False, 
                    state_transition_history=False
                ),
                skills=skills,
                version=agent.get("agentRuntimeVersion", "1"),
                metadata={
                    "agent_id": agent_id,
                    "agent_url": agent_url,
                    "runtime_arn": agent.get("agentRuntimeArn"),
                    "last_updated": agent.get("lastUpdatedAt"),
                    "deployment_method": "web_api",
                    "platform": "aws-bedrock-agentcore",
                    "model": "anthropic.claude-3-haiku-20240307-v1:0",
                    "region": "us-east-1",
                }
            )
            
            # Return the agent card as dict for JSON serialization
            return agent_card.model_dump()

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
                # Extract the message and call the agent directly
                message_text = str(request.get("message", ""))
                if not message_text:
                    message_text = "Hello"
                
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

        @self.a2a_router.post("/a2a/agent/{agent_id}/jsonrpc")
        async def handle_jsonrpc_request(agent_id: str, request: Dict[str, Any]):
            """JSON-RPC endpoint for A2A agent communication

            NOTE: Currently experiencing AWS permissions issue with AgentCore invocation.
            Error: "User is not authorized to access this resource" on InvokeAgentRuntime operation.

            WORKAROUND: Attach AWS managed policy 'BedrockAgentCoreFullAccess' to user,
            or investigate specific IAM permissions required for AgentCore runtime invocation.

            The JSON-RPC endpoint structure is correctly implemented and ready once
            permissions are resolved.
            """
            if agent_id not in self.a2a_apps:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            # The A2A SDK should handle the JSON-RPC request
            # Since we're in FastAPI, we need to delegate to the Starlette app
            # This is a simplified version - we may need to handle ASGI properly
            try:
                # Call AgentCore directly
                payload = {"prompt": str(request)}
                raw_result = await self.client.invoke_agent(agent_id, payload)

                # Translate AgentCore response to JSON-RPC format
                # AgentCore returns: {"result": {"role": "assistant", "content": [{"text": "..."}]}}
                if isinstance(raw_result, dict) and "result" in raw_result and "content" in raw_result["result"]:
                    # Extract text from AgentCore format
                    text_parts = []
                    for content_item in raw_result["result"]["content"]:
                        if isinstance(content_item, dict) and "text" in content_item:
                            text_parts.append(content_item["text"])
                    response_text = "".join(text_parts).strip()

                    # Return JSON-RPC response format - ARK expects direct text in result field
                    return {"result": response_text}

                return raw_result
            except Exception as e:
                logger.error(f"JSON-RPC request failed for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

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
                    # Create HTTP client for streaming
                    from .agentcore_http_client import AgentCoreHTTPClient

                    http_client = AgentCoreHTTPClient(region="us-east-1")

                    async for chunk in http_client.invoke_agent_stream(agent_id, prompt):
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

                # Create HTTP client for this agent
                http_client = AgentCoreHTTPClient(region="us-east-1")

                # Create agent executor
                executor = AgentCoreExecutor(http_client, agent_id)

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

                logger.info(f"Registered agent {agent_id} -> /a2a/agent/{agent_id} (with JSON-RPC support)")

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
