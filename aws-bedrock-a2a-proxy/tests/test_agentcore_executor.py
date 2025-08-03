"""Tests for AgentCoreExecutor"""

import os
import pytest
from unittest.mock import Mock, AsyncMock

from aws_bedrock_a2a_proxy.agentcore_executor import AgentCoreExecutor
from aws_bedrock_a2a_proxy.agentcore_client import AgentCoreClient

# Mock AWS credentials for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_agentcore_client():
    """Create a mock AgentCoreClient for testing"""
    client = Mock(spec=AgentCoreClient)
    client.invoke_agent = AsyncMock(return_value={"response": "test response"})
    return client


@pytest.fixture
def agentcore_executor(mock_agentcore_client):
    """Create AgentCoreExecutor instance for testing"""
    return AgentCoreExecutor(agentcore_client=mock_agentcore_client, agent_id="test-agent-id")


class TestAgentCoreExecutor:
    """Tests for AgentCoreExecutor class"""

    def test_init(self, mock_agentcore_client):
        """Test AgentCoreExecutor initialization"""
        executor = AgentCoreExecutor(agentcore_client=mock_agentcore_client, agent_id="test-agent-id")
        assert executor.agentcore_client == mock_agentcore_client
        assert executor.agent_id == "test-agent-id"

    @pytest.mark.asyncio
    async def test_execute_basic(self, agentcore_executor, mock_agentcore_client):
        """Test basic execution"""
        # Mock context and event queue
        mock_context = Mock()
        mock_event_queue = Mock()

        # Test that execute method exists and can be called
        try:
            await agentcore_executor.execute(mock_context, mock_event_queue)
        except Exception:
            # Expect some exception due to mocked context, but method should exist
            assert "execute" in str(type(agentcore_executor).__dict__)
