"""
Configuration module for AWS Bedrock A2A Proxy

This module provides a centralized configuration system that loads settings from
environment variables with appropriate defaults and type conversion.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Configuration settings for the AWS Bedrock A2A Proxy server."""

    # Agent Configuration
    agent_refresh_interval_seconds: int
    enable_streaming: bool
    enable_description_as_a2a_skill: bool

    # Server Configuration
    host: str  # Binding address
    port: int  # Binding port
    expose_host: str  # Advertised host (for external URLs)
    expose_port: int  # Advertised port (for external URLs)
    base_path: str  # Base path for URLs
    log_level: str  # Logging level

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Get basic values first
        host = os.getenv("HOST", "localhost")
        port = int(os.getenv("PORT", "2972"))

        return cls(
            # Agent Configuration
            agent_refresh_interval_seconds=int(os.getenv("AGENT_REFRESH_INTERVAL_SECONDS", "30")),
            enable_streaming=os.getenv("ENABLE_STREAMING", "1") == "1",
            enable_description_as_a2a_skill=os.getenv("ENABLE_DESCRIPTION_AS_A2A_SKILL", "1") == "1",
            # Server Configuration
            host=host,
            port=port,
            expose_host=os.getenv("EXPOSE_HOST", host),
            expose_port=int(os.getenv("EXPOSE_PORT", str(port))),
            base_path=os.getenv("BASE_PATH", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    def get_base_url(self) -> str:
        """Get the base URL for the server."""
        return f"http://{self.expose_host}:{self.expose_port}{self.base_path}"


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance, loading it if necessary."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
