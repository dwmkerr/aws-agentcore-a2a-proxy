"""
AgentCore Executor

This module handles the execution of requests to AWS Bedrock AgentCore agents.
It bridges A2A requests to AgentCore agent invocations.
"""

import logging
import uuid
from typing import Any

from a2a.types import Message, Part, Role, TextPart

from .agentcore_client import AgentCoreClient
from .agentcore_streaming_invocation_client import AgentCoreStreamingInvocationClient

logger = logging.getLogger(__name__)


class AgentCoreExecutor:
    """Agent executor that bridges A2A requests to AWS Bedrock AgentCore agents"""

    def __init__(self, agentcore_client: AgentCoreClient, streaming_client: AgentCoreStreamingInvocationClient, agent_id: str):
        self.agentcore_client = agentcore_client
        self.streaming_client = streaming_client
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
                role=Role.AGENT,
                parts=[
                    Part(root=TextPart(text=f"Error executing agent: {str(e)}"))
                ]
            )
            await event_queue.put(error_message)

    def _should_use_streaming(self, context: Any) -> bool:
        """Check if streaming should be used based on context"""
        try:
            if hasattr(context, 'streaming') and context.streaming:
                return True
            return False
        except Exception:
            return False

    async def _execute_streaming(self, context: Any, event_queue: Any, message_text: str) -> None:
        """Execute agent with streaming response"""
        try:
            logger.info(f"Streaming execution requested for agent {self.agent_id}")
            
            # Stream response from AgentCore using streaming client
            async for chunk in self.streaming_client.invoke_agent_stream(self.agent_id, message_text):
                # Extract text from chunk
                chunk_text = self._extract_chunk_text(chunk)
                
                if chunk_text:
                    # Create streaming message
                    stream_message = Message(
                        message_id=str(uuid.uuid4()),
                        context_id=(
                            context.message.context_id if context.message and context.message.context_id else str(uuid.uuid4())
                        ),
                        role=Role.AGENT,
                        parts=[
                            Part(root=TextPart(text=chunk_text))
                        ]
                    )
                    
                    # Send chunk via event queue
                    await event_queue.put(stream_message)
                    logger.debug(f"Sent streaming chunk: {chunk_text[:50]}...")
                    
            logger.info(f"Streaming execution completed for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Streaming execution failed for agent {self.agent_id}: {e}")
            raise
            
    def _extract_chunk_text(self, chunk: Any) -> str:
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

    async def _execute_single_response(self, context: Any, event_queue: Any, message_text: str) -> None:
        """Execute agent with single response"""
        try:
            # Call AgentCore agent
            response = await self.agentcore_client.invoke_agent(self.agent_id, {"prompt": message_text})

            # Extract response text from AgentCore response
            response_text = ""
            if isinstance(response, dict):
                if "result" in response:
                    result = response["result"]
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            first_content = content[0]
                            if isinstance(first_content, dict) and "text" in first_content:
                                response_text = first_content["text"]

            if not response_text:
                response_text = "No response received from agent"

            # Create A2A response message
            response_message = Message(
                message_id=str(uuid.uuid4()),
                context_id=(
                    context.message.context_id if context.message and context.message.context_id else str(uuid.uuid4())
                ),
                role=Role.AGENT,
                parts=[
                    Part(root=TextPart(text=response_text))
                ]
            )

            # Send response to event queue
            await event_queue.put(response_message)

        except Exception as e:
            logger.error(f"Single response execution failed for agent {self.agent_id}: {e}")
            raise