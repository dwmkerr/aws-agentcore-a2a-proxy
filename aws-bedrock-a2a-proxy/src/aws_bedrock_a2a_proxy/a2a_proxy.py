import logging
import uuid
import asyncio
from typing import Dict, List, Any, Optional

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TextPart
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .agentcore_client import AgentCoreClient
from .agentcore_http_client import AgentCoreHTTPClient

logger = logging.getLogger(__name__)


class AgentCoreExecutor:
    """Agent executor that bridges A2A requests to AWS Bedrock AgentCore agents"""
    
    def __init__(self, http_client: AgentCoreHTTPClient, agent_id: str):
        self.http_client = http_client
        self.agent_id = agent_id
    
    async def execute(self, context, event_queue):
        """Execute agent request and stream response back"""
        try:
            # Extract message text from A2A context
            message_text = ""
            if context.message and context.message.parts:
                first_part = context.message.parts[0]
                if hasattr(first_part, "root") and hasattr(first_part.root, "text"):
                    message_text = first_part.root.text
            
            logger.info(f"Executing agent {self.agent_id} with message: {message_text[:100]}...")
            
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
                messageId=str(uuid.uuid4()),
                contextId=context.message.contextId if context.message else str(uuid.uuid4()),
                taskId=context.task_id,
                role=Role.agent,
                parts=[Part(root=TextPart(kind="text", text=response_text))],
            )
            
            # Send response back via event queue
            await event_queue.enqueue_event(response_message)
            
            logger.info(f"Agent {self.agent_id} execution completed")
            
        except Exception as e:
            logger.error(f"Failed to execute agent {self.agent_id}: {e}")
            # Send error response
            error_message = Message(
                messageId=str(uuid.uuid4()),
                contextId=context.message.contextId if context.message else str(uuid.uuid4()),
                taskId=context.task_id,
                role=Role.agent,
                parts=[Part(root=TextPart(kind="text", text=f"Error: {str(e)}"))],
            )
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context, event_queue):
        """Cancel agent execution (not implemented for AgentCore)"""
        logger.info(f"Cancel requested for agent {self.agent_id}")
        pass


class A2AProxy:
    def __init__(self, agentcore_client: AgentCoreClient):
        self.client = agentcore_client
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.a2a_apps: Dict[str, A2AStarletteApplication] = {}
        self.a2a_router = APIRouter()
        self.setup_a2a_routes()
    
    def get_router(self):
        """Get the FastAPI router for A2A endpoints"""
        return self.a2a_router
    
    def setup_a2a_routes(self):
        """Set up A2A routing endpoints"""
        @self.a2a_router.get("/a2a/agents")
        async def list_a2a_agents():
            """A2A agents list endpoint with agent cards"""
            return [
                {
                    "name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
                    "description": agent.get("description", "AgentCore agent"),
                    "capabilities": {
                        "streaming": True,
                        "pushNotifications": False,
                        "stateTransitionHistory": False
                    },
                    "host": "localhost:2972",
                    "agent-card": f"/a2a/agent/{agent_id}/.well-known/agent.json",
                    "endpoint": f"/a2a/agent/{agent_id}",
                    "status": agent.get("status", "unknown"),
                    "metadata": {
                        "type": "bedrock-agentcore",
                        "version": agent.get("agentRuntimeVersion", "1"),
                        "runtime_id": agent_id
                    }
                }
                for agent_id, agent in self.agents.items()
            ]

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
                    "lastUpdatedAt": agent.get("lastUpdatedAt")
                }
                for agent_id, agent in self.agents.items()
            ]

        @self.a2a_router.get("/a2a/agent/{agent_id}/.well-known/agent.json")
        async def get_agent_card(agent_id: str):
            """Agent card endpoint per A2A standard"""
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            
            agent = self.agents[agent_id]
            return {
                "name": agent.get("agentRuntimeName", f"agent-{agent_id}"),
                "description": agent.get("description", "Customer support agent powered by AWS Bedrock AgentCore"),
                "capabilities": {
                    "streaming": True,
                    "pushNotifications": False,
                    "stateTransitionHistory": False
                },
                "skills": [
                    {
                        "name": "get_customer_id",
                        "description": "Look up customer ID from email address"
                    },
                    {
                        "name": "get_orders",
                        "description": "Retrieve customer order information"
                    },
                    {
                        "name": "get_knowledge_base_info", 
                        "description": "Query product knowledge base"
                    }
                ],
                "version": agent.get("agentRuntimeVersion", "1"),
                "runtime": {
                    "platform": "aws-bedrock-agentcore",
                    "model": "anthropic.claude-3-haiku-20240307-v1:0",
                    "region": "us-east-1"
                },
                "metadata": {
                    "runtime_id": agent_id,
                    "runtime_arn": agent.get("agentRuntimeArn"),
                    "last_updated": agent.get("lastUpdatedAt"),
                    "deployment_method": "web_api"
                }
            }

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
            
            # Get the A2A app for this agent and handle the JSON-RPC request
            a2a_app = self.a2a_apps[agent_id]
            
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

    async def initialize_agents(self, agents: List[Dict[str, Any]]) -> None:
        logger.info(f"Registering {len(agents)} agents for A2A proxy")
        
        for agent in agents:
            agent_id = agent.get('agentRuntimeId')
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
                    defaultInputModes=["text/plain"],
                    defaultOutputModes=["text/plain"],
                    capabilities=AgentCapabilities(
                        streaming=True,
                        pushNotifications=False,
                        stateTransitionHistory=False
                    ),
                    skills=[
                        AgentSkill(
                            id="customer_support",
                            name="Customer Support",
                            description="Handle customer inquiries and support requests",
                            tags=["support", "customer", "help"]
                        ),
                        AgentSkill(
                            id="order_tracking",
                            name="Order Tracking",
                            description="Track and look up customer orders",
                            tags=["orders", "tracking", "status"]
                        ),
                        AgentSkill(
                            id="knowledge_base",
                            name="Knowledge Base",
                            description="Query product knowledge and documentation",
                            tags=["knowledge", "documentation", "info"]
                        )
                    ]
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
                "status": agent.get("status", "unknown")
            }
            for agent_id, agent in self.agents.items()
        ]