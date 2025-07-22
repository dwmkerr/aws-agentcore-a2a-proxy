# AWS Bedrock AgentCore A2A Proxy

A2A proxy server for AWS Bedrock AgentCore agents.

## Quickstart

```bash
# Show all available recipes
make help

# Install dependencies
make init

# Run in development mode
make dev
```

## API Endpoints

```
GET  /                                           # server health
POST /rpc/discover                               # discover agents
GET  /status                                     # server status
GET  /agents                                     # raw agent data
GET  /a2a-addresses                              # A2A addresses

GET  /a2a/agents                                 # A2A agent list
GET  /a2a/agent/{id}/.well-known/agent.json     # agent card
POST /a2a/agent/{id}/jsonrpc                    # JSON-RPC endpoint
POST /agents/{id}/invoke                         # direct invocation
```

Usage:
- Discover agents: `curl -X POST http://localhost:2972/rpc/discover`
- List A2A agents: `curl http://localhost:2972/a2a/agents`
- Invoke agent: `curl -X POST http://localhost:2972/agents/{id}/invoke -d '{"prompt":"test"}'`

## How It Works

Uses direct HTTPS calls to AgentCore (boto3 SDK not available yet). Discovers agents via `bedrock-agentcore-control` client and exposes them through standard A2A protocol endpoints. Supports both explicit credentials and default AWS credential chain.

Requires IAM permissions:
- `bedrock-agentcore:ListAgentRuntimes`
- `bedrock-agentcore:DescribeAgentRuntime` 
- `bedrock-agentcore:InvokeAgentRuntime`