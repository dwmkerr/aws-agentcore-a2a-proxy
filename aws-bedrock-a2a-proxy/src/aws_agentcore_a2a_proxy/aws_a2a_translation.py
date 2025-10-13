"""
AWS AgentCore to A2A Protocol Translation

This module handles the translation between AWS Bedrock AgentCore agent data
and A2A protocol format with explicit types for all data structures.
"""

from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass
import json
import uuid
import logging
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Message, TextPart, Part, Role

logger = logging.getLogger(__name__)


@dataclass
class AgentCoreAgent:
    """Type representing an AWS AgentCore agent as returned by the discovery API"""

    agent_runtime_id: str
    agent_runtime_name: str
    agent_runtime_arn: str
    description: Optional[str]
    status: str  # "READY", "CREATING", etc.
    version: str  # "1", "2", etc.
    last_updated_at: str  # ISO timestamp

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCoreAgent":
        """Create AgentCoreAgent from raw API response dictionary"""
        return cls(
            agent_runtime_id=data["agentRuntimeId"],
            agent_runtime_name=data["agentRuntimeName"],
            agent_runtime_arn=data["agentRuntimeArn"],
            description=data.get("description"),
            status=data["status"],
            version=data.get("version", data.get("agentRuntimeVersion", "1")),
            last_updated_at=data["lastUpdatedAt"],
        )


def agentcore_agent_to_agentcard(
    agent_id: str,
    agent_data: Dict[str, Any],
    base_url: str = "http://localhost:2972",
    streaming_enabled: bool = True,
    description_as_skill: bool = True,
) -> Dict[str, Any]:
    """
    Convert an AgentCore agent to an A2A Agent Card

    Args:
        agent_id: The AgentCore agent runtime ID
        agent_data: Raw AgentCore agent data dictionary
        base_url: Base URL for the A2A proxy

    Returns:
        Dictionary representing an A2A Agent Card
    """
    # Parse the AgentCore agent data
    agent = AgentCoreAgent.from_dict(agent_data)

    # Create A2A Agent Card using the SDK
    agent_card = AgentCard(
        protocol_version="0.2.6",
        name=agent.agent_runtime_name,
        description=agent.description,
        url=f"{base_url}/a2a/agent/{agent_id}",
        preferred_transport="JSONRPC",
        version=agent.version,
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        capabilities=AgentCapabilities(
            streaming=streaming_enabled, push_notifications=False, state_transition_history=False
        ),
        skills=_generate_skills_from_agent(agent, description_as_skill),
    )

    return agent_card.model_dump()


def _generate_skills_from_agent(agent: AgentCoreAgent, description_as_skill: bool) -> List[AgentSkill]:
    """Generate A2A skills from AgentCore agent metadata"""
    skills = []

    # Use description as skill if enabled and available
    if description_as_skill and agent.description:
        skills.append(AgentSkill(id="description", name="Description", description=agent.description, tags=["general"]))

    return skills


def a2a_request_to_agentcore_payload(a2a_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract message from A2A JSON-RPC request to AgentCore payload format

    Args:
        a2a_request: A2A JSON-RPC request with params.message.parts[0].text

    Returns:
        AgentCore payload format: {"prompt": "text"}

    Raises:
        ValueError: If message text cannot be extracted
    """
    if not isinstance(a2a_request, dict) or "params" not in a2a_request:
        raise ValueError("Invalid A2A request: missing params")

    params = a2a_request["params"]
    if "message" not in params or "parts" not in params["message"]:
        raise ValueError("Invalid A2A request: missing params.message.parts")

    parts = params["message"]["parts"]
    if not parts or not isinstance(parts, list) or len(parts) == 0:
        raise ValueError("Invalid A2A request: empty message parts")

    # Concatenate all text parts to form complete message
    message_parts = []
    for part in parts:
        if isinstance(part, dict) and "text" in part:
            text_content = part["text"]
            if text_content:
                message_parts.append(text_content)

    if not message_parts:
        raise ValueError("Invalid A2A request: no text content in message parts")

    message_text = " ".join(message_parts)
    return {"prompt": message_text}


def agentcore_response_to_a2a_message(
    agentcore_response: Dict[str, Any], request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert AgentCore response to A2A JSON-RPC response format

    Args:
        agentcore_response: AgentCore client response
        request_id: JSON-RPC request ID

    Returns:
        A2A JSON-RPC response with proper Message format or error
    """
    req_id = request_id or str(uuid.uuid4())

    # Check if AgentCore returned a proper error
    if "error" in agentcore_response:
        error_msg = agentcore_response["error"]
        logger.error(f"AgentCore returned error: {error_msg}")
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(error_msg)}}

    # Extract text from AgentCore response
    response_text = _extract_text_from_agentcore_response(agentcore_response)
    logger.debug(f"AgentCore response success: {len(response_text)} chars")

    # Create A2A Message using SDK types
    response_message = Message(
        message_id=str(uuid.uuid4()), role=Role.agent, parts=[Part(TextPart(text=response_text))]
    )

    # Return JSON-RPC success response
    return {"jsonrpc": "2.0", "id": req_id, "result": response_message.model_dump()}


def agentcore_streaming_to_a2a_chunks(
    agentcore_response: Dict[str, Any], request_id: Optional[str] = None
) -> Iterator[str]:
    """
    Convert AgentCore streaming response to A2A Server-Sent Events format

    Args:
        agentcore_response: AgentCore client streaming response
        request_id: JSON-RPC request ID

    Yields:
        A2A-compliant SSE chunks with JSON-RPC format
    """
    req_id = request_id or str(uuid.uuid4())

    if agentcore_response.get("streaming", False):
        # Handle actual streaming response - accumulate all chunks to ensure completeness
        response_iterator = agentcore_response["response"]
        accumulated_text = []

        for line in response_iterator.iter_lines(chunk_size=10):
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]  # Remove 'data: ' prefix
                if line == "[DONE]":
                    break

                try:
                    # Parse the AgentCore chunk
                    chunk_data = json.loads(line)
                    chunk_text = _extract_text_from_chunk(chunk_data)

                    if chunk_text:
                        accumulated_text.append(chunk_text)

                        # Send each chunk immediately for real-time streaming
                        chunk_message = Message(
                            message_id=str(uuid.uuid4()), role=Role.agent, parts=[Part(TextPart(text=chunk_text))]
                        )

                        # Format as JSON-RPC response
                        a2a_chunk = {"jsonrpc": "2.0", "id": req_id, "result": chunk_message.model_dump()}

                        yield f"data: {json.dumps(a2a_chunk)}\n\n"

                except json.JSONDecodeError:
                    # Handle non-JSON streaming data
                    if line.strip():
                        line_text = line.strip()
                        accumulated_text.append(line_text)

                        chunk_message = Message(
                            message_id=str(uuid.uuid4()), role=Role.agent, parts=[Part(TextPart(text=line_text))]
                        )

                        a2a_chunk = {"jsonrpc": "2.0", "id": req_id, "result": chunk_message.model_dump()}

                        yield f"data: {json.dumps(a2a_chunk)}\n\n"

        # Log the complete accumulated response for debugging
        complete_response = "".join(accumulated_text)
        logger.info(f"Complete streaming response length: {len(complete_response)} chars")
        logger.debug(f"Complete streaming response: {complete_response[:200]}...")

    else:
        # Handle single response as one chunk
        response_text = _extract_text_from_agentcore_response(agentcore_response)

        chunk_message = Message(
            message_id=str(uuid.uuid4()), role=Role.agent, parts=[Part(TextPart(text=response_text))]
        )

        a2a_chunk = {"jsonrpc": "2.0", "id": req_id, "result": chunk_message.model_dump()}

        yield f"data: {json.dumps(a2a_chunk)}\n\n"

    # A2A streaming ends naturally - no [DONE] marker needed


def _extract_text_from_agentcore_response(agentcore_response: Dict[str, Any]) -> str:
    """Extract text content from AgentCore client response"""
    if agentcore_response.get("streaming", False):
        # If we get streaming response, collect all chunks
        response_parts = []
        if "response" in agentcore_response:
            for line in agentcore_response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(line)
                        chunk_text = _extract_text_from_chunk(chunk_data)
                        if chunk_text:
                            response_parts.append(chunk_text)
                    except json.JSONDecodeError:
                        if line.strip():
                            response_parts.append(line.strip())
        return "".join(response_parts)
    else:
        # Handle regular JSON response
        if "result" in agentcore_response:
            return _extract_text_from_chunk(agentcore_response["result"])
        return str(agentcore_response)


def _extract_text_from_chunk(chunk: Any) -> str:
    """Extract text content from AgentCore response chunk"""
    if isinstance(chunk, dict):
        if "result" in chunk and isinstance(chunk["result"], dict):
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
        elif "text" in chunk:
            return chunk["text"]
    return str(chunk) if chunk else ""
