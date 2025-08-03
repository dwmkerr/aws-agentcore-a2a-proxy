"""AWS Bedrock AgentCore A2A Proxy."""

from .a2a_proxy_server import app
from .main import setup_app

__all__ = [
    "app",
    "setup_app",
]
