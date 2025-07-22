import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

from aws_bedrock_a2a_proxy.main import app


@pytest.fixture
def mock_app_state():
    mock_client = Mock()
    mock_proxy = Mock()
    mock_agents = [
        {
            "agentId": "test-agent-1",
            "agentName": "Test Agent 1",
            "status": "READY",
            "agentArn": "arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/test-agent-1"
        }
    ]
    
    app.state.client = mock_client
    app.state.proxy = mock_proxy
    app.state.agents = mock_agents
    
    mock_proxy.running_servers = {"test-agent-1": Mock()}
    mock_proxy.invoke_agent = AsyncMock(return_value={"response": "test response"})
    
    return mock_client, mock_proxy, mock_agents


def test_root():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "AWS Bedrock AgentCore A2A Server is running"}


def test_status_endpoint(mock_app_state):
    mock_client, mock_proxy, mock_agents = mock_app_state
    
    with TestClient(app) as client:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["agents_discovered"] == 1
        assert data["a2a_servers_running"] == 1
        assert len(data["agents"]) == 1
        assert data["agents"][0]["agent_id"] == "test-agent-1"


def test_list_agents(mock_app_state):
    mock_client, mock_proxy, mock_agents = mock_app_state
    
    with TestClient(app) as client:
        response = client.get("/agents")
        assert response.status_code == 200
        assert response.json() == mock_agents