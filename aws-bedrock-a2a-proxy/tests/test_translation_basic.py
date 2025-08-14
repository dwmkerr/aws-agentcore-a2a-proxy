#!/usr/bin/env python3
"""
Basic tests for AWS AgentCore to A2A translation functions.
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest  # noqa: E402
from aws_agentcore_a2a_proxy.aws_a2a_translation import (  # noqa: E402
    agentcore_agent_to_agentcard,
    a2a_request_to_agentcore_payload,
)


class TestBasicTranslation:
    """Basic tests for translation functions that actually exist"""

    def test_agentcore_agent_to_agentcard(self):
        """Test converting AgentCore agent data to A2A agent card"""
        agent_data = {
            "agentRuntimeId": "test-agent-123",
            "agentRuntimeName": "test_agent",
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test-agent-123",
            "description": "Test agent for AWS operations",
            "status": "READY",
            "version": "1",
            "lastUpdatedAt": "2024-01-01T00:00:00Z",
        }

        result = agentcore_agent_to_agentcard("test-agent-123", agent_data)

        # Should be a valid agent card structure
        assert "name" in result
        assert "description" in result
        assert "capabilities" in result
        assert result["name"] == "test_agent"

    def test_a2a_request_to_agentcore_payload(self):
        """Test extracting prompt from A2A request"""
        a2a_request = {
            "jsonrpc": "2.0",
            "method": "message",
            "params": {"message": {"parts": [{"text": "list my s3 buckets"}]}},
            "id": "test-789",
        }

        result = a2a_request_to_agentcore_payload(a2a_request)
        assert result == {"prompt": "list my s3 buckets"}

    def test_a2a_request_invalid_structure(self):
        """Test A2A request with invalid structure"""
        invalid_request = {"invalid": "request"}

        with pytest.raises(ValueError):
            a2a_request_to_agentcore_payload(invalid_request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
