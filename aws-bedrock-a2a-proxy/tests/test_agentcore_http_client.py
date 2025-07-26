"""Tests for AgentCoreHTTPClient"""

import pytest
from unittest.mock import Mock, patch

from aws_bedrock_a2a_proxy.agentcore_http_client import AgentCoreHTTPClient


@pytest.fixture
def http_client():
    """Create AgentCoreHTTPClient instance for testing"""
    return AgentCoreHTTPClient(region="us-east-1")


@pytest.fixture
def mock_session():
    """Mock boto3 session"""
    session = Mock()
    credentials = Mock()
    credentials.access_key = "test-access-key"
    credentials.secret_key = "test-secret-key"
    session.get_credentials.return_value = credentials
    return session


@pytest.fixture
def mock_response():
    """Mock requests response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"result": {"role": "assistant", "content": [{"text": "Test response"}]}}
    return response


class TestAgentCoreHTTPClient:
    """Test cases for AgentCoreHTTPClient"""

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.boto3.Session")
    def test_init_with_credentials(self, mock_session_class):
        """Test initialization with explicit credentials"""
        client = AgentCoreHTTPClient(region="us-west-2", access_key_id="test-key", secret_access_key="test-secret")

        assert client.region == "us-west-2"
        assert client.access_key_id == "test-key"
        assert client.secret_access_key == "test-secret"

    def test_init_default_region(self):
        """Test initialization with default region"""
        client = AgentCoreHTTPClient()
        assert client.region == "us-east-1"

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.boto3.Session")
    def test_get_session_with_credentials(self, mock_session_class):
        """Test session creation with explicit credentials"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = AgentCoreHTTPClient(access_key_id="test-key", secret_access_key="test-secret")

        session = client._get_session()

        mock_session_class.assert_called_once_with(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret", region_name="us-east-1"
        )
        assert session == mock_session

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.boto3.Session")
    def test_get_session_default_credentials(self, mock_session_class):
        """Test session creation with default credentials"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = AgentCoreHTTPClient()
        session = client._get_session()

        mock_session_class.assert_called_once_with(region_name="us-east-1")
        assert session == mock_session

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.requests.get")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.SigV4Auth")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.BotocoreAWSRequest")
    def test_list_agents_success(self, mock_request_class, mock_auth_class, mock_get, http_client, mock_session):
        """Test successful agent listing"""
        # Mock request and auth
        mock_request = Mock()
        mock_request.url = "https://test-url.com"
        mock_request.headers = {"Authorization": "test-auth"}
        mock_request_class.return_value = mock_request

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "agentRuntimes": [
                {"agentRuntimeId": "agent-1", "agentRuntimeName": "Test Agent 1"},
                {"agentRuntimeId": "agent-2", "agentRuntimeName": "Test Agent 2"},
            ]
        }
        mock_get.return_value = mock_response

        # Mock session
        with patch.object(http_client, "_get_session", return_value=mock_session):
            # Run test
            import asyncio

            agents = asyncio.run(http_client.list_agents())

        # Verify results
        assert len(agents) == 2
        assert agents[0]["agentRuntimeId"] == "agent-1"
        assert agents[1]["agentRuntimeId"] == "agent-2"

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "bedrock-agentcore-control.us-east-1.amazonaws.com" in call_args[1]["headers"]["Authorization"]

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.requests.get")
    def test_list_agents_failure(self, mock_get, http_client, mock_session):
        """Test agent listing failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access denied"
        mock_get.return_value = mock_response

        with patch.object(http_client, "_get_session", return_value=mock_session):
            with pytest.raises(Exception) as exc_info:
                import asyncio

                asyncio.run(http_client.list_agents())

        assert "Failed to list agents: 403 - Access denied" in str(exc_info.value)

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.requests.post")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.SigV4Auth")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.BotocoreAWSRequest")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.uuid.uuid4")
    def test_invoke_agent_success(
        self, mock_uuid, mock_request_class, mock_auth_class, mock_post, http_client, mock_session
    ):
        """Test successful agent invocation"""
        # Mock UUID
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value="test-session-id")

        # Mock request and auth
        mock_request = Mock()
        mock_request.url = "https://test-url.com"
        mock_request.headers = {"Authorization": "test-auth", "Content-Type": "application/json"}
        mock_request.data = '{"prompt": "test prompt"}'
        mock_request_class.return_value = mock_request

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"role": "assistant", "content": [{"text": "Agent response"}]}}
        mock_post.return_value = mock_response

        with patch.object(http_client, "_get_session", return_value=mock_session):
            # Run test
            import asyncio

            result = asyncio.run(http_client.invoke_agent("test-agent", "test prompt"))

        # Verify results
        assert result["result"]["content"][0]["text"] == "Agent response"

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"] == '{"prompt": "test prompt"}'
        assert "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id" in dict(mock_request.headers)

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.requests.post")
    def test_invoke_agent_failure(self, mock_post, http_client, mock_session):
        """Test agent invocation failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        with patch.object(http_client, "_get_session", return_value=mock_session):
            with pytest.raises(Exception) as exc_info:
                import asyncio

                asyncio.run(http_client.invoke_agent("test-agent", "test prompt"))

        assert "Agent invocation failed: 500 - Internal server error" in str(exc_info.value)

    def test_get_agent_arn(self, http_client):
        """Test agent ARN construction"""
        arn = http_client._get_agent_arn("test-agent-123")
        expected_arn = "arn:aws:bedrock-agentcore:us-east-1:705383350627:runtime/test-agent-123"
        assert arn == expected_arn

    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.SigV4Auth")
    @patch("aws_bedrock_a2a_proxy.agentcore_http_client.BotocoreAWSRequest")
    def test_create_signed_request(self, mock_request_class, mock_auth_class, http_client, mock_session):
        """Test signed request creation"""
        # Mock request
        mock_request = Mock()
        mock_request_class.return_value = mock_request

        # Mock auth
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth

        with patch.object(http_client, "_get_session", return_value=mock_session):
            result = http_client._create_signed_request(
                "POST", "https://test.com", '{"test": "data"}', {"Content-Type": "application/json"}
            )

        # Verify request creation
        mock_request_class.assert_called_once_with(
            method="POST", url="https://test.com", data='{"test": "data"}', headers={"Content-Type": "application/json"}
        )

        # Verify auth was applied
        mock_auth.add_auth.assert_called_once_with(mock_request)
        assert result == mock_request
