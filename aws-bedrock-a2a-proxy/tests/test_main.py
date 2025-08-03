import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from aws_bedrock_a2a_proxy.main import create_app

# Mock AWS credentials for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def test_app():
    """Create test app instance"""
    return create_app(enable_lifespan=False)


@patch("aws_bedrock_a2a_proxy.main.AgentCoreClient")
def test_root(mock_client_class, test_app):
    """Test root endpoint"""
    # Mock the client to avoid AWS calls
    mock_client_class.return_value = Mock()

    with TestClient(test_app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@patch("aws_bedrock_a2a_proxy.main.AgentCoreClient")
def test_create_app(mock_client_class):
    """Test app creation"""
    mock_client_class.return_value = Mock()

    app = create_app(enable_lifespan=False)
    assert app is not None
    assert hasattr(app, "routes")
    assert len(app.routes) > 0
