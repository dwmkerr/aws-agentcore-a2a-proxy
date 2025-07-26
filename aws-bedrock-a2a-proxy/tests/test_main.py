import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from aws_bedrock_a2a_proxy.main import app

# Mock AWS credentials for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_app_state():
    mock_client = AsyncMock()
    mock_proxy = Mock()
    mock_agents = [
        {
            "agentId": "test-agent-1",
            "agentName": "Test Agent 1",
            "status": "READY",
            "agentArn": "arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/test-agent-1",
        }
    ]

    # Configure the mock client
    mock_client.list_agents = AsyncMock(return_value=mock_agents)

    # Configure the mock proxy with async methods
    mock_proxy.initialize_agents = AsyncMock()
    mock_proxy.shutdown = AsyncMock()
    mock_proxy.running_servers = {"test-agent-1": Mock()}
    mock_proxy.invoke_agent = AsyncMock(return_value={"response": "test response"})

    app.state.client = mock_client
    app.state.proxy = mock_proxy
    app.state.agents = mock_agents

    return mock_client, mock_proxy, mock_agents


@patch('aws_bedrock_a2a_proxy.main.discover_and_refresh_agents')
def test_root(mock_discover):
    # Mock the discovery function to prevent AWS calls during startup
    mock_discover.return_value = {"agents": []}

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "AWS Bedrock AgentCore A2A Server is running"}


@patch('aws_bedrock_a2a_proxy.main.discover_and_refresh_agents')
def test_status_endpoint(mock_discover, mock_app_state):
    mock_client, mock_proxy, mock_agents = mock_app_state
    mock_discover.return_value = {"agents": mock_agents}

    with TestClient(app) as client:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["agents_discovered"] == 1
        assert data["a2a_servers_running"] == 1
        assert len(data["agents"]) == 1
        assert data["agents"][0]["agent_id"] == "test-agent-1"


@patch('aws_bedrock_a2a_proxy.main.discover_and_refresh_agents')
def test_list_agents(mock_discover, mock_app_state):
    mock_client, mock_proxy, mock_agents = mock_app_state
    mock_discover.return_value = {"agents": mock_agents}

    with TestClient(app) as client:
        response = client.get("/agents")
        assert response.status_code == 200
        assert response.json() == mock_agents
