"""Tests for A2AProxy"""

import os
import pytest
from unittest.mock import Mock, AsyncMock

from aws_bedrock_a2a_proxy.a2a_proxy_server import A2AProxy
from aws_bedrock_a2a_proxy.agentcore_client import AgentCoreClient

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
    return A2AProxy(agentcore_client=mock_agentcore_client)


class TestA2AProxy:
    """Tests for A2AProxy class"""

    def test_init(self, mock_agentcore_client):
        """Test A2AProxy initialization"""
        proxy = A2AProxy(agentcore_client=mock_agentcore_client)
        assert proxy.client == mock_agentcore_client
        assert proxy.agents == {}
        assert proxy.a2a_router is not None

    def test_init_without_client(self):
        """Test A2AProxy initialization without client"""
        proxy = A2AProxy()
        assert proxy.client is None
        assert proxy.agents == {}
        assert proxy.a2a_router is not None

    def test_setup_a2a_routes(self, a2a_proxy):
        """Test that A2A routes are set up"""
        # Check that the router has routes
        assert len(a2a_proxy.a2a_router.routes) > 0

        # Check for expected route paths
        route_paths = [route.path for route in a2a_proxy.a2a_router.routes]
        assert any("/a2a/" in path for path in route_paths)
        assert any("/agentcore/" in path for path in route_paths)
