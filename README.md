# AWS Bedrock AgentCore A2A Proxy

[![codecov](https://codecov.io/gh/dwmkerr/aws-agentcore-a2a-proxy/graph/badge.svg?token=aXkZtiSQ57)](https://codecov.io/gh/dwmkerr/aws-agentcore-a2a-proxy) [![PyPI version](https://badge.fury.io/py/aws-agentcore-a2a-proxy.svg)](https://pypi.org/project/aws-agentcore-a2a-proxy/)

A2A proxy server for AWS Bedrock AgentCore agents.

- Polls AWS Agentcore to discover agents
- Exposes an A2A Agent Card for each agent
- Operates as proxy, transforming A2A calls to AWS Bedrock invocation

The screenshot below shows some agents in Agentcore, the proxy discovering and exposing them, and the A2A Inspector connected to one of the agents:

![Screenshot of AWS Agentcore Proxy](./docs/agentcore-proxy-a2a.png)

Each exposed agent has its own agent card and A2A address. This allows systems that do not know about Agentcore to talk to your agents.

> [!WARNING]
> This is an example of how to expose Agentcore agents via A2A, by running a simple proxy server. Agentcore is currently in tech preview. The demo deploys an AWS agent that runs with a configurable role. Be very mindful of the roles that you assign agents and the potential security consequences. 

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   A2A       │───▶│  A2A Proxy      │───▶│   AgentCore     │
│   Client    │    │                 │    │                 │
│             │◀───│                 │◀───│                 │
└─────────────┘    └─────────────────┘    └─────────────────┘
                           │
                           ▼
                   Auto-discovers agents
                   Exposes A2A endpoints
```

<!-- vim-markdown-toc GFM -->

- [Quickstart](#quickstart)
    - [Running from Source](#running-from-source)
    - [Using as a Python Package](#using-as-a-python-package)
- [Calling Agentcore Agents via A2A](#calling-agentcore-agents-via-a2a)
- [Testing with A2A Inspector](#testing-with-a2a-inspector)
- [Direct AgentCore Access (Non-A2A)](#direct-agentcore-access-non-a2a)
- [Additional Features](#additional-features)
    - [External URL Configuration](#external-url-configuration)
    - [Streaming Responses](#streaming-responses)
- [Demo Setup](#demo-setup)
    - [Demo Agent - GitHub Dev Assistant](#demo-agent---github-dev-assistant)
- [Next Steps](#next-steps)

<!-- vim-markdown-toc -->

## Quickstart

The Agentcore A2A Proxy uses the AWS credential chain to discover Agentcore agents. This means you can configure explicit credentials via environment variables, use the service account, or any other configuration method.

### Running from Source

First, clone and navigate to the repository:

```bash
git clone https://github.com/dwmkerr/aws-agentcore-a2a-proxy.git
cd aws-agentcore-a2a-proxy
```

For convenience, the server will read from `.env` if present - you can drop your AWS credentials in this file:

```bash
# Configure environment
cp .env.example .env
vi .env
```

Start the AWS Agentcore A2A Proxy with:

```bash
make dev

# Starting AWS Bedrock AgentCore A2A Proxy
# Configuration:
# • Agent Refresh Interval: 30s
# • Streaming Enabled: True
# • Description as A2A Skill: True
# • Server: http://localhost:2972
# polling: discovered 2 agents: aws_operator_agent (v11), github_dev_assistant (v12)
```

Any agents available for the user with the given credentials will be exposed. If you need to create some agents as an example, set up the required AWS infrastructure and deploy some sample agents:

```bash
# Set up demo AWS infrastructure (IAM roles, ECR, CloudWatch, etc.)
make install-demo-infrastructure

# Deploy sample agents using the infrastructure
make install-demo-agents
```

### Using as a Python Package

Install the package:

```bash
pip install aws-agentcore-a2a-proxy
```

Run directly:

```bash
python -m aws_agentcore_a2a_proxy

# Or run with uv - note that 'pip install' is not needed in this case.
uv run --with aws-agentcore-a2a-proxy python -m aws_agentcore_a2a_proxy
```

Or use in your Python scripts:

```python
from aws_agentcore_a2a_proxy.main import create_app
import uvicorn

app = create_app()
uvicorn.run(app, host="localhost", port=2972)
```

## Calling Agentcore Agents via A2A

View the API documentation:

```bash
open http://localhost:2972/docs
```

List available A2A agents:

```bash
curl http://localhost:2972/a2a/agents

# [{"agent_id": "Bedrock_Customer_Support_Agent-jQwAm25rmZ", "name": "Bedrock_Customer_Support_Agent", "host": "localhost:2972", "endpoint": "/a2a/agent/Bedrock_Customer_Support_Agent-jQwAm25rmZ", ...}]
```

Get the agent ID dynamically:

```bash
AGENT_ID=$(curl -s http://localhost:2972/a2a/agents | jq -r '.[0].agent_id')
echo "Using agent ID: $AGENT_ID"
```

Get an agent's card:

```bash
curl http://localhost:2972/a2a/agent/$AGENT_ID/.well-known/agent.json

# {"name": "Bedrock_Customer_Support_Agent", "description": "Customer support agent powered by AWS Bedrock AgentCore", "capabilities": {...}}
```

Invoke an agent via A2A:

```bash
curl -X POST http://localhost:2972/a2a/agent/$AGENT_ID/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"method": "query", "params": {"query": "Hello, I need help with my order"}, "id": 1}'

# Output: {"result": "Hello! I'd be happy to help you with your order..."}
```

## Testing with A2A Inspector

You can test your A2A proxy using the A2A Inspector tool:

```bash
git clone https://github.com/a2aproject/a2a-inspector.git
cd a2a-inspector
chmod +x run.sh
./run.sh
```

Open http://localhost:5001 and enter your A2A agent URL (e.g., `http://localhost:2972/a2a/agent/YOUR_AGENT_ID`) to interact with your agents through a web interface.

## Direct AgentCore Access (Non-A2A)

For debugging or direct integration, you can also call AgentCore agents directly without the A2A protocol.

List the Agentcore agents first:

```bash
curl http://localhost:2972/agentcore/agents

# [{"agentRuntimeId": "Bedrock_Customer_Support_Agent-XLA7bpGvk5", "agentRuntimeName": "Bedrock_Customer_Support_Agent", "status": "READY", ...}]
```

Get the agent runtime ID for direct AgentCore calls:

```bash
AGENT_RUNTIME_ID=$(curl -s http://localhost:2972/agentcore/agents | jq -r '.[0].agentRuntimeId')
echo "Using agent runtime ID: $AGENT_RUNTIME_ID"
```

Then invoke:

```bash
curl -X POST http://localhost:2972/agentcore/agents/$AGENT_RUNTIME_ID/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, I need help with my order"}'

# {"result": {"role": "assistant", "content": [{"text": "Hello! I'd be happy to help..."}]}}
```

## Additional Features

### External URL Configuration

Configure external URLs when running behind proxies or load balancers:

```bash
export EXPOSE_HOST=my-domain.com
export EXPOSE_PORT=443
```

The server binds to `host:port` internally but advertises `expose_host:expose_port` in A2A agent cards. This can be useful In scenarios where the host and the agent card url differs - for example the host in a Kubernetes Pod will be `0.0.0.0` but it will be advertised via its external address such as `http://aws-agentcore-bridge.default.svc.cluster.local:80`.

### Streaming Responses

The A2A proxy supports streaming responses through both the A2A protocol and direct HTTP endpoints. Agents declare streaming capability in their agent cards:

```json
{
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  }
}
```

You can make a streaming call like so:

```bash
# Get the agent runtime ID (using jq to extract dynamically)
AGENT_RUNTIME_ID=$(curl -s http://localhost:2972/agentcore/agents | jq -r '.[0].agentRuntimeId')

# Make streaming call
curl -X POST http://localhost:2972/agentcore/agents/$AGENT_RUNTIME_ID/invoke-stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"prompt": "Tell me a very long and detailed story about Agent-to-Agent (A2A) protocol, including its history, how it works, its benefits, and real-world applications. Please make it comprehensive and engaging."}'

# Output (streaming in real-time):
# data: {"text": "Once"}
# data: {"text": " upon"}
# data: {"text": " a"}
# data: {"text": " time"}
# data: {"text": " in"}
# data: {"text": " the"}
# data: {"text": " world"}
# data: {"text": " of"}
# data: {"text": " distributed"}
# data: {"text": " systems"}
# data: {"text": "..."}
# data: [DONE]
```

## Demo Setup

If you want to try the complete demo with managed infrastructure and agents:

```bash
# Set up demo infrastructure (IAM roles, ECR, CloudWatch, etc.)
make install-demo-infrastructure

# Deploy demo agents using the infrastructure
make install-demo-agents

# Or deploy specific agents only, e.g:
# cd demo/agents/customer-support-agents
# make install    # deploy agent
# make uninstall  # remove agent

# Clean up everything when done
make uninstall-demo-infrastructure
```

The demo infrastructure includes:
- IAM execution role for AgentCore agents
- ECR repository for container images
- User policies for agent invocation
- CloudWatch log groups with retention
- Bedrock model logging configuration

Configure resources by editing `./demo/infrastructure/terraform.tfvars`. Note these resources incur AWS costs.

### Demo Agent - GitHub Dev Assistant

GitHub Development Assistant Agent using GitHub's MCP server for PR management, issue tracking, and CI/CD monitoring.

Run the agent locally:

```bash
# Create GitHub token: https://github.com/settings/tokens
export GITHUB_TOKEN=ghp_your_token_here
cd demo/agents/github-dev-assistant
make dev
```

Test with commands:

```bash
# Basic test
curl -X POST http://localhost:9595/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, what can you help me with?"}'

# With Authorization header (overrides env token)  
curl -X POST http://localhost:9595/invocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ghp_your_token" \
  -d '{"prompt": "Show me my pull requests"}'
```

## Next Steps

- Streaming test end to end
- OIDC integration
