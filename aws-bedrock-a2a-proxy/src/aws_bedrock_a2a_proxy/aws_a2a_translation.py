"""
AWS AgentCore to A2A Protocol Translation

This module handles the translation between AWS Bedrock AgentCore agent data
and A2A protocol format with explicit types for all data structures.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from a2a.types import AgentCard, AgentCapabilities


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
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCoreAgent':
        """Create AgentCoreAgent from raw API response dictionary"""
        return cls(
            agent_runtime_id=data["agentRuntimeId"],
            agent_runtime_name=data["agentRuntimeName"], 
            agent_runtime_arn=data["agentRuntimeArn"],
            description=data.get("description"),
            status=data["status"],
            version=data.get("version", data.get("agentRuntimeVersion", "1")),
            last_updated_at=data["lastUpdatedAt"]
        )




def agentcore_agent_to_agentcard(agent_id: str, agent_data: Dict[str, Any], base_url: str = "http://localhost:2972") -> Dict[str, Any]:
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
        description=agent.description or f"AgentCore agent: {agent.agent_runtime_name}",
        url=f"{base_url}/a2a/agent/{agent_id}",
        preferred_transport="JSONRPC",
        version=agent.version,
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,  
            state_transition_history=False
        ),
        skills=[]  # No hardcoded skills - let the agent provide its own capabilities
    )
    
    return agent_card.model_dump()