# AWS Bedrock AgentCore A2A Proxy

TODO:

- [ ] aws agent working tested via a2a inspector
- [ ] stream

[![PyPI version](https://badge.fury.io/py/aws-bedrock-a2a-proxy.svg)](https://badge.fury.io/py/aws-bedrock-a2a-proxy)
[![codecov](https://codecov.io/gh/dwmkerr/aws-bedrock-a2a-proxy/branch/main/graph/badge.svg)](https://codecov.io/gh/dwmkerr/aws-bedrock-a2a-proxy)

A2A proxy server for AWS Bedrock AgentCore agents.

This server connects to a given AWS account, discovers AgentCore agents, and then exposes them via A2A. This allows you to call your AgentCore agents over the A2A protocol. Each exposed agent has its own agent card and A2A address.

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

Features:

- Expose any Bedrock agent via A2A
- Automatic polling to discover Bedrock agents
- Endpoints to show all agents available
- Invoke agent via A2A
- Streaming responses

## Quickstart

**AWS Credentials:** The proxy uses the standard AWS credential chain (environment variables, `~/.aws/credentials`, IAM roles, etc.) and also reads from a local `.env` file if present.

Setup your AWS credentials by editing `.env`:

```bash
# Configure environment
cp .env.example .env
vi .env
```

Start the AWS Bedrock A2A Proxy with:

```bash
make dev
```

**Development without AWS:** To run without AWS connectivity (useful for development):

```bash
# Temporarily disable AWS credentials
AWS_ACCESS_KEY_ID="" AWS_SECRET_ACCESS_KEY="" make dev
```

Any agents available for the user with the given credentials will be exposed. If you need to create some agents as an example, set up the required AWS infrastructure and deploy some sample agents:

```bash
# Set up demo AWS infrastructure (IAM roles, ECR, CloudWatch, etc.)
make install-demo-infrastructure

# Deploy sample agents using the infrastructure
make install-demo-agents
```

## Calling Bedrock Agents via A2A

View the API documentation:

```bash
open http://localhost:2972/docs
```

List available A2A agents:

```bash
curl http://localhost:2972/a2a/agents

# [{"agent_id": "Bedrock_Customer_Support_Agent-jQwAm25rmZ", "name": "Bedrock_Customer_Support_Agent", "host": "localhost:2972", "endpoint": "/a2a/agent/Bedrock_Customer_Support_Agent-jQwAm25rmZ", ...}]
```

Get an agent's card:

```bash
# Get the agent ID dynamically:
AGENT_ID=$(curl -s http://localhost:2972/a2a/agents | jq -r '.[0].agent_id')

curl http://localhost:2972/a2a/agent/$AGENT_ID/.well-known/agent.json

# {"name": "Bedrock_Customer_Support_Agent", "description": "Customer support agent powered by AWS Bedrock AgentCore", "capabilities": {...}}
```

Invoke an agent via A2A:

```bash
# Get the agent ID dynamically:
AGENT_ID=$(curl -s http://localhost:2972/a2a/agents | jq -r '.[0].agent_id')

curl -X POST http://localhost:2972/a2a/agent/$AGENT_ID/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"method": "query", "params": {"query": "Hello, I need help with my order"}, "id": 1}'

# Output: {"result": "Hello! I'd be happy to help you with your order..."}
```

## Direct AgentCore Access (Non-A2A)

For debugging or direct integration, you can also call AgentCore agents directly without the A2A protocol.

List the Agentcore agents first:

```bash
curl http://localhost:2972/agentcore/agents

# [{"agentRuntimeId": "Bedrock_Customer_Support_Agent-XLA7bpGvk5", "agentRuntimeName": "Bedrock_Customer_Support_Agent", "status": "READY", ...}]
```

Invoke directly:

```bash
# Get the agent runtime ID dynamically:
AGENT_RUNTIME_ID=$(curl -s http://localhost:2972/agentcore/agents | jq -r '.[0].agentRuntimeId')

curl -X POST http://localhost:2972/agentcore/agents/$AGENT_RUNTIME_ID/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, I need help with my order"}'

# {"result": {"role": "assistant", "content": [{"text": "Hello! I'd be happy to help..."}]}}
```

## Additional Features

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
# Get the agent runtime ID dynamically:
AGENT_RUNTIME_ID=$(curl -s http://localhost:2972/agentcore/agents | jq -r '.[0].agentRuntimeId')

curl -X POST http://localhost:2972/agentcore/agents/$AGENT_RUNTIME_ID/invoke-stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"prompt": "Tell me a story about A2A protocol"}'

# Output (streaming in real-time):
# data: {"text": "Once"}
# data: {"text": " upon"}
# data: {"text": " a"}
# data: {"text": " time"}
# data: [DONE]
```

## Demo Agents

This project includes demonstration agents showcasing different AgentCore capabilities:

### GitHub Development Assistant

A GitHub workflow assistant that demonstrates OIDC authentication and role-based access control. Uses GitHub's hosted MCP server for real-time GitHub data access.

**Features**: Personalized PR/issue management, notifications, CI/CD monitoring, role-aware responses (developer/team_lead/admin)

**Testing**:
```bash
# Deploy agent (no GitHub token needed - uses OIDC)
cd demo/agents/github-dev-assistant
export IAM_ROLE_ARN="arn:aws:iam::account:role/bedrock-agent-role" 
make deploy

# Configure OIDC via Bedrock console for GitHub authentication
# Access via Bedrock console with GitHub login
# Agent extracts GitHub token from OIDC claims for API calls
```

Users login with GitHub OAuth, AWS Bedrock handles the authentication flow, and the agent receives verified user claims for personalized GitHub workflow assistance.

### AWS Operator Agent

An AWS operations assistant that demonstrates AWS CLI integration and infrastructure management. Provides secure, role-based AWS operations through authenticated CLI commands.

**Features**: EC2/S3/Lambda management, CloudWatch monitoring, cost analysis, identity management, role-based access control (readonly/operator/admin)

**Testing**:
```bash
# Deploy agent (requires AWS CLI and credentials)
cd demo/agents/aws-operator-agent
export IAM_ROLE_ARN="arn:aws:iam::account:role/bedrock-agent-role"
make deploy

# Configure OIDC via Bedrock console for role-based access
# Access via Bedrock console with corporate SSO
# Agent executes AWS CLI commands based on user's role and permissions
```

Users authenticate via OIDC, agent determines their AWS role from groups, and executes secure AWS CLI operations with appropriate access controls.

## TODO

- [ ] Add OIDC authentication support
