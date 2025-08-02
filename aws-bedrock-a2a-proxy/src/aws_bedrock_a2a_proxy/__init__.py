"""AWS Bedrock AgentCore A2A Proxy."""

from .main import (
    create_app,
    create_main_router,
    create_a2a_router,
    aws_proxy_startup,
    aws_proxy_shutdown,
    get_server_config,
)

__all__ = [
    "create_app",
    "create_main_router",
    "create_a2a_router",
    "aws_proxy_startup",
    "aws_proxy_shutdown",
    "get_server_config",
]
