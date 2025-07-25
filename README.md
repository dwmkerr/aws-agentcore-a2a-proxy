# AWS Bedrock AgentCore A2A Proxy

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

## Quickstart

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
curl http://localhost:2972/a2a/agent/Bedrock_Customer_Support_Agent-jQwAm25rmZ/.well-known/agent.json

# {"name": "Bedrock_Customer_Support_Agent", "description": "Customer support agent powered by AWS Bedrock AgentCore", "capabilities": {...}}
```

Invoke an agent via A2A:

```bash
curl -X POST http://localhost:2972/a2a/agent/Bedrock_Customer_Support_Agent-f48aKO5EGS/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"method": "query", "params": {"query": "Hello, I need help with my order"}, "id": 1}'

# Output: {"result": "Hello! I'd be happy to help you with your order..."}
```

## Direct AgentCore Access (Non-A2A)

For debugging or direct integration, you can also call AgentCore agents directly without the A2A protocol.

List the Agentcore agents first:

```bash
curl http://localhost:2972/agentcore/agents

# [{"agentRuntimeId": "Bedrock_Customer_Support_Agent-f48aKO5EGS", "agentRuntimeName": "Bedrock_Customer_Support_Agent", "status": "READY", ...}]
```

Then invoke:

```bash
curl -X POST http://localhost:2972/agentcore/agents/Bedrock_Customer_Support_Agent-f48aKO5EGS/invoke \
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

**Current Implementation:**
- Streaming is enabled in agent capabilities
- Direct streaming endpoint available at `/agentcore/agents/{agent_id}/invoke-stream`
- A2A protocol supports streaming through event queues
- Compatible with Server-Sent Events (SSE) for real-time responses

**Direct Streaming Usage:**
Test streaming responses directly:

```bash
# Stream responses via Server-Sent Events
curl -X POST http://localhost:2972/agentcore/agents/Bedrock_Customer_Support_Agent-f48aKO5EGS/invoke-stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"prompt": "Hello, tell me a story"}'

# Output (streaming):
# data: {"text": "Once"}
# data: {"text": " upon"}
# data: {"text": " a time"}
# data: [DONE]
```

**A2A Streaming Implementation:**
The A2A protocol automatically handles streaming when supported by the underlying AgentCore runtime:

1. **AgentCore Streaming**: Modify HTTP client to handle streaming responses
   ```python
   # Future implementation example
   async def invoke_agent_stream(self, agent_id: str, prompt: str):
       async for chunk in self.stream_invoke(agent_id, prompt):
           yield chunk
   ```

2. **A2A Stream Handling**: Send partial responses via event queue
   ```python
   # Future AgentCoreExecutor enhancement
   async for chunk in self.http_client.invoke_agent_stream(agent_id, prompt):
       partial_message = Message(
           messageId=str(uuid.uuid4()),
           contextId=context.message.contextId,
           taskId=context.task_id,
           role=Role.agent,
           parts=[Part(root=TextPart(kind="text", text=chunk))],
       )
       await event_queue.enqueue_event(partial_message)
   ```

3. **Client Usage**: A2A clients would receive multiple message events
   ```bash
   # Streaming responses appear as multiple JSON-RPC notifications
   {"result": "Hello"}
   {"result": " there"}
   {"result": "! How"}
   {"result": " can I help?"}
   ```

**Note**: Streaming requires AgentCore runtime support for streaming invocations, which may depend on the underlying model and AWS Bedrock configuration.

## How It Works

Uses direct HTTPS calls to AgentCore (boto3 SDK not available yet). Discovers agents via `bedrock-agentcore-control` client and exposes them through standard A2A protocol endpoints. Supports both explicit credentials and default AWS credential chain.

## Demo Setup (Complete Infrastructure + Agents)

If you want to try the complete demo with managed infrastructure and agents:

```bash
# Set up demo infrastructure (IAM roles, ECR, CloudWatch, etc.)
make install-demo-infrastructure

# Deploy demo agents using the infrastructure
make install-demo-agents

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

## Custom Infrastructure Setup

If you have your own AWS infrastructure and want to deploy agents to it:

1. **Set environment variables:**
   ```bash
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_REGION=us-east-1
   export IAM_ROLE_ARN=arn:aws:iam::123456789012:role/YourAgentRole
   export ECR_REPOSITORY_URL=123456789012.dkr.ecr.us-east-1.amazonaws.com/your-repo
   ```

2. **Deploy specific agents:**
   ```bash
   cd demo/agents/customer-support-agents
   make install    # deploy agent
   make uninstall  # remove agent
   ```

This creates a customer support agent with order lookup and knowledge base capabilities.


## Permissions

Requires IAM permissions:
- `bedrock-agentcore:ListAgentRuntimes`
- `bedrock-agentcore:DescribeAgentRuntime` 
- `bedrock-agentcore:InvokeAgentRuntime`

## TODO

- [x] Extract AgentCoreHTTPClient from AgentCoreExecutor
- [x] Add unit tests with mocked HTTP responses  
- [ ] Add OIDC authentication support
- [ ] Add support for streaming responses
