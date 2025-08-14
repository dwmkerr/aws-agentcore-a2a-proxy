#!/usr/bin/env python3
"""
Entry point for running the AWS Bedrock A2A Proxy as a module.

Usage:
    python -m aws_agentcore_a2a_proxy
    uv run -m aws_agentcore_a2a_proxy
"""

import uvicorn
from .main import create_app
from .config import get_config

if __name__ == "__main__":
    app = create_app()
    config = get_config()
    uvicorn.run(app, host=config.host, port=config.port, reload=True)
