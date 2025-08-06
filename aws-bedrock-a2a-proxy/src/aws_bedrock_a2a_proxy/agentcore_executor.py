"""
AgentCore Executor

This module handles the execution of requests to AWS Bedrock AgentCore agents.
It bridges A2A requests to AgentCore agent invocations.
"""

import json
import logging
import uuid
from typing import Any, Optional

from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
)

from .agentcore_client import AgentCoreClient

# AgentCoreStreamingInvocationClient removed - AgentCoreClient now handles both streaming and non-streaming

logger = logging.getLogger(__name__)


class AgentCoreExecutor:
    """Agent executor that bridges A2A requests to AWS Bedrock AgentCore agents"""

    def __init__(self, agentcore_client: AgentCoreClient, agent_id: str):
        self.agentcore_client = agentcore_client
        self.agent_id = agent_id

    async def execute(self, context: Any, event_queue: Any) -> None:
        """Execute agent request using A2A SDK streaming events"""
        try:
            # Extract message text from A2A context
            message_text = ""
            if context.message and context.message.parts:
                first_part = context.message.parts[0]
                if hasattr(first_part, "root") and hasattr(first_part.root, "text"):
                    message_text = first_part.root.text

            logger.info(f"Executing agent {self.agent_id} with message: {message_text[:100]}...")

            # Generate task and context IDs for A2A tracking
            task_id = str(uuid.uuid4())
            context_id = (
                context.message.context_id
                if context.message and hasattr(context.message, "context_id")
                else str(uuid.uuid4())
            )

            # Send initial task status - working
            await self._send_task_status(event_queue, task_id, context_id, TaskState.working, final=False)

            # Call AgentCore with unified client
            response = await self.agentcore_client.invoke_agent(self.agent_id, {"prompt": message_text})

            # Handle response based on whether it's streaming or not
            if response.get("streaming", False):
                await self._handle_streaming_response(event_queue, task_id, context_id, response)
            else:
                await self._handle_single_response(event_queue, task_id, context_id, response)

            # Send final task status - completed
            await self._send_task_status(event_queue, task_id, context_id, TaskState.completed, final=True)

        except Exception as e:
            logger.error(f"Failed to execute agent {self.agent_id}: {e}")
            # Send error status
            task_id = str(uuid.uuid4())
            context_id = (
                context.message.context_id
                if context.message and hasattr(context.message, "context_id")
                else str(uuid.uuid4())
            )
            await self._send_task_status(
                event_queue, task_id, context_id, TaskState.failed, final=True, error_message=str(e)
            )

    async def _send_task_status(
        self,
        event_queue: Any,
        task_id: str,
        context_id: str,
        state: TaskState,
        final: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Send task status update using A2A SDK types"""
        try:
            # Create task status with current timestamp
            from datetime import datetime

            current_timestamp = datetime.utcnow().isoformat() + "Z"
            task_status = TaskStatus(state=state, timestamp=current_timestamp)

            # Add error message if failed
            if state == TaskState.failed and error_message:
                # Create error message using A2A Message type
                error_msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[Part(root=TextPart(text=f"Error: {error_message}"))],
                )
                task_status.message = error_msg

            # Create status update event
            status_event = TaskStatusUpdateEvent(
                task_id=task_id, context_id=context_id, status=task_status, final=final, kind="status-update"
            )

            await event_queue.put(status_event)
            logger.debug(f"Sent task status: {state} (final: {final})")

        except Exception as e:
            logger.error(f"Failed to send task status: {e}")

    async def _handle_streaming_response(self, event_queue: Any, task_id: str, context_id: str, response: dict) -> None:
        """Handle streaming response using A2A artifact updates"""
        try:
            logger.info("Processing streaming response from AWS")

            # Get the response iterator from AWS
            response_iterator = response["response"]

            for line in response_iterator.iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]  # Remove 'data: ' prefix
                    if line == "[DONE]":
                        break

                    try:
                        # Parse the chunk
                        chunk_data = json.loads(line)

                        # Extract text from chunk
                        chunk_text = self._extract_text_from_chunk(chunk_data)

                        if chunk_text:
                            # Send as artifact update
                            await self._send_artifact_update(event_queue, task_id, context_id, chunk_text)

                    except json.JSONDecodeError:
                        # Handle non-JSON streaming data
                        if line.strip():
                            await self._send_artifact_update(event_queue, task_id, context_id, line.strip())

        except Exception as e:
            logger.error(f"Failed to handle streaming response: {e}")
            raise

    async def _handle_single_response(self, event_queue: Any, task_id: str, context_id: str, response: dict) -> None:
        """Handle single JSON response as one artifact update"""
        try:
            logger.info("Processing single JSON response from AWS")

            # Extract text from the response
            response_text = ""
            if "result" in response:
                result = response["result"]
                response_text = self._extract_text_from_chunk(result)

            if not response_text:
                response_text = "No response received from agent"

            # Send as single artifact update
            await self._send_artifact_update(event_queue, task_id, context_id, response_text)

        except Exception as e:
            logger.error(f"Failed to handle single response: {e}")
            raise

    async def _send_artifact_update(self, event_queue: Any, task_id: str, context_id: str, text: str) -> None:
        """Send artifact update using A2A SDK types"""
        try:
            # Import Artifact type
            from a2a.types import Artifact

            # Create artifact with the text content
            artifact = Artifact(artifact_id="response-artifact", parts=[Part(TextPart(text=text))])

            # Create artifact update event
            artifact_event = TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=artifact,
                append=False,  # For now, don't append
                last_chunk=False,  # Let the caller determine this
                kind="artifact-update",
            )

            await event_queue.put(artifact_event)
            logger.debug(f"Sent artifact update: {text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to send artifact update: {e}")

    def _extract_text_from_chunk(self, chunk: Any) -> str:
        """Extract text content from AWS response chunk"""
        if isinstance(chunk, dict):
            # Handle various chunk formats
            if "text" in chunk:
                return chunk["text"]
            elif "result" in chunk and isinstance(chunk["result"], dict):
                if "content" in chunk["result"]:
                    content = chunk["result"]["content"]
                    if isinstance(content, list) and content:
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                text_parts.append(item["text"])
                        return "".join(text_parts)
                elif "text" in chunk["result"]:
                    return chunk["result"]["text"]
            elif "delta" in chunk and isinstance(chunk["delta"], dict):
                # Handle delta-style streaming
                if "text" in chunk["delta"]:
                    return chunk["delta"]["text"]

        return str(chunk) if chunk else ""
