"""Tests for A2AProxy"""

import os
import pytest
from unittest.mock import Mock, AsyncMock

from aws_bedrock_a2a_proxy.a2a_proxy_server import A2AProxy
from aws_bedrock_a2a_proxy.agentcore_client import AgentCoreClient
from aws_bedrock_a2a_proxy.config import get_config

# Mock AWS credentials for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_agentcore_client():
    """Create a mock AgentCoreClient for testing"""
    client = Mock(spec=AgentCoreClient)
    client.list_agents = AsyncMock(return_value=[])
    return client


@pytest.fixture
def a2a_proxy(mock_agentcore_client):
    """Create A2AProxy instance for testing"""
    config = get_config()
    return A2AProxy(config, mock_agentcore_client)


class TestA2AProxy:
    """Tests for A2AProxy class"""

    def test_init(self, mock_agentcore_client):
        """Test A2AProxy initialization"""
        config = get_config()
        proxy = A2AProxy(config, mock_agentcore_client)
        assert proxy.client == mock_agentcore_client
        assert proxy.agents == {}
        assert hasattr(proxy, "routes")  # FastAPI has routes
        assert proxy.title == "AWS Bedrock AgentCore A2A Server"

    def test_init_requires_client(self):
        """Test A2AProxy initialization requires client"""
        config = get_config()
        # This should fail since client is required
        with pytest.raises(TypeError):
            A2AProxy(config)

    def test_setup_routes(self, a2a_proxy):
        """Test that routes are set up"""
        # Check that the app has routes
        assert len(a2a_proxy.routes) > 0

        # Check for expected route paths
        route_paths = [route.path for route in a2a_proxy.routes]
        assert any("/a2a/" in path for path in route_paths)
        assert any("/agentcore/" in path for path in route_paths)
        assert any(path == "/" for path in route_paths)  # Root route
        assert any(path == "/health" for path in route_paths)  # Health route
