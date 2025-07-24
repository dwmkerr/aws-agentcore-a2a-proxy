# AWS Bedrock AgentCore A2A Proxy

A2A proxy server for AWS Bedrock AgentCore agents.

## Quickstart

Setup your AWS credentials by editing `.env`:

```bash
# Configure environment
cp .env.example .env
vi .env
```

Any agents available for the user with the given credentials will be exposed. If you need to create demo agents, check [Setting Up Demo AWS Resources](#setting-up-demo-aws-resources).

```bash
# Setup AWS infrastructure
cd demo/infrastructure/
terraform init && terraform apply

# Configure environment
cp .env.example .env
# Add IAM_ROLE_ARN from terraform output to .env

# Install dependencies and run
make init
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

## Setting Up Demo AWS Resources

You can set up resources on your AWS account to run the demo. These resources are in `demo/infrastructure` and include:

- IAM execution role for AgentCore agents
- User policies for agent invocation
- CloudWatch log groups with retention
- Bedrock model logging configuration

You can configure the details of resources by editing `./demo/infrastructure/terraform.tfvars`. Note that these resources will incur cost, check AWS pricing for details.

Create demo resources with:

```bash
cd demo/infrastructure
terraform init
terraform apply
```

To clean up these resources use:

```bash
terraform destroy
```

## Setting Up Demo Agents

Once you have demo infrastructure you can create demo agents with:

TODO

This will create TODO

To delete these agents, run TODO

## Infrastructure

```bash
cd demo/infrastructure/
terraform destroy  # cleanup when done
```

## Permissions

Requires IAM permissions:
- `bedrock-agentcore:ListAgentRuntimes`
- `bedrock-agentcore:DescribeAgentRuntime` 
- `bedrock-agentcore:InvokeAgentRuntime`

## TODO

- [x] Extract AgentCoreHTTPClient from AgentCoreExecutor
- [x] Add unit tests with mocked HTTP responses  
- [x] Update to a2a-sdk>=0.2.12 to match agents-at-scale
- [ ] Simplify Makefile to follow AI Developer Guide patterns
- [ ] Add OIDC authentication support
- [ ] Add retry logic for AgentCore API calls
- [ ] Add request/response logging and metrics
- [ ] Add configuration validation and error handling
- [ ] Add health check endpoint for AgentCore connectivity
- [ ] Add support for streaming responses
- [ ] Add rate limiting for agent invocations
- [ ] Add caching for agent discovery results
