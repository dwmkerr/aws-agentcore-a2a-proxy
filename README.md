# AWS Bedrock AgentCore A2A Proxy

TODO:

- [ ] aws agent working tested via a2a inspector
- [ ] stream
- [ ] lint style as mine
- [x] agent runtime release versions seem to not update - fixed with architecture-specific AWS CLI
- [x] otel - disabled for local testing

## TODO

- [ ] Add OIDC authentication support

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

## Demoing the AWS Operator Agent

Here's a complete walkthrough of the AWS Operator Agent.

First install the demo agents:

```bash
make install-demo-agents
```

Next you can test the agent through the AWS Agentcore playground: https://us-east-1.console.aws.amazon.com/bedrock-agentcore/playground?region=us-east-1

Use an input such as:

```json
{"prompt": "give me the names of all my s3 buckets"}
```

Now run the AWS Bedrock A2A proxy locally:

```bash
make dev

# output, e.g:
# INFO: polling: discovered 2 agents: aws_operator_agent (v2), github_dev_assistant (v2)
```

Curl the A2A or Agentcore agents endpoints to show the agents:

```bash
curl -s http://localhost:2972/agentcore/agents | jq '.[]'

# output, e.g:
{
  "agentRuntimeId": "aws_operator_agent-ehXYYSF6ET",
  "agentRuntimeName": "aws_operator_agent",
  "status": "READY",
  "version": "2",
  "etc": "..."
}
```

You can call the agent via the Agentcore endpoint - the proxy will use the AWS APIs directly:

```bash
curl -s -X POST "http://localhost:2972/agentcore/agents/aws_operator_agent-ehXYYSF6ET/invoke" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "give me the names of all my s3 buckets"}' | jq '.result.content[0].text'
```

You can also show the A2A agents:

```bash
curl -s http://localhost:2972/a2a/agents | jq '.[]'

# output, e.g:
{
  "name": "aws_operator_agent",
  "preferredTransport": "JSONRPC",
  "protocolVersion": "0.2.6",
  "url": "http://localhost:2972/a2a/agent/aws_operator_agent-ehXYYSF6ET"
}
```

The `url` shown can be opened in the A2A inspector and you can make calls directly through the UI.

Finally, you can call the agent via the A2A protocol directly:

```bash
curl -s -X POST "http://localhost:2972/a2a/agent/aws_operator_agent-ehXYYSF6ET" \
  -H "Content-Type: application/json" \
  -d '{"message": "give me the names of all my s3 buckets"}' | jq '.result.parts[0].text'
```

All three methods should return your S3 bucket names, demonstrating the complete AgentCore → A2A integration.

Delete the agents and infrastructure with:

```bash
make uninstall-demo-agents
make uninstall-demo-infrastructure
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

