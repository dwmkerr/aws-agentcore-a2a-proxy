.PHONY: help configure deploy test-local test-remote status invoke-local invoke-remote clean
.DEFAULT_GOAL := help

# Load environment variables from root .env
ifneq (,$(wildcard ../../.env))
    include ../../.env
    export
endif

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-env: ## Check required environment variables
	@echo "Checking environment variables..."
	@test -n "$(AWS_ACCESS_KEY_ID)" || (echo "Error: AWS_ACCESS_KEY_ID not set in ../../.env" && exit 1)
	@test -n "$(AWS_SECRET_ACCESS_KEY)" || (echo "Error: AWS_SECRET_ACCESS_KEY not set in ../../.env" && exit 1)
	@test -n "$(AWS_REGION)" || (echo "Error: AWS_REGION not set in ../../.env" && exit 1)
	@test -n "$(IAM_ROLE_ARN)" || (echo "Error: IAM_ROLE_ARN not set in ../../.env" && exit 1)
	@echo "✅ All required environment variables are set"

install: ## Install agent dependencies
	pip install strands-agents strands-agents-tools bedrock-agentcore bedrock-agentcore-starter-toolkit

configure: check-env ## Configure the agent for deployment (legacy - not used by deploy)
	@echo "⚠️  Note: configure is not needed for web API deployment"
	agentcore configure --entrypoint agent.py --execution-role $(IAM_ROLE_ARN)

test-local: configure ## Launch and test agent locally
	@echo "🚀 Launching agent locally..."
	@echo "ℹ️  Agent will start at http://localhost:8080"
	@echo "📝 In another terminal, run: make invoke-local"
	@echo "🔄 Or test with: agentcore invoke --local '{\"prompt\": \"Hello, I need help with my order\"}'"
	@echo ""
	agentcore launch --local

test-remote: ## Test deployed agent
	@echo "🧪 Testing remote agent..."
	agentcore invoke '{"prompt": "From: me@example.net - Hi, I bought a smartphone from your store. I am traveling to Europe next week, will I be able to use the charger? Also, I struggle to remove the cover. Thanks, Danilo"}'

deploy: check-env ## Deploy agent to AWS via web API (use AGENT_NAME=foo for custom name)
	@echo "📦 DEPLOYING: $(if $(AGENT_NAME),$(AGENT_NAME),Bedrock_Customer_Support_Agent)"
	@echo "🔧 What will be created:"
	@echo "   • AgentCore runtime with container"
	@echo "   • ECR image: 705383350627.dkr.ecr.us-east-1.amazonaws.com/bedrock_agentcore-agent:latest"
	@echo "   • IAM execution role: $(IAM_ROLE_ARN)"
	@echo "   • Network: PUBLIC access"
	@echo "   • Protocol: HTTP"
	@echo ""
	@echo "ℹ️  Using direct API calls because AgentCore CLI is broken in preview"
	python deploy-via-api.py "$(if $(AGENT_NAME),$(AGENT_NAME),Bedrock_Customer_Support_Agent)" 705383350627.dkr.ecr.us-east-1.amazonaws.com/bedrock_agentcore-agent:latest $(IAM_ROLE_ARN)
	@echo ""
	@echo "✅ DEPLOYMENT COMPLETE!"
	@echo "🎯 Next steps:"
	@echo "   1. Call: curl -X POST http://localhost:2972/rpc/initialize"
	@echo "   2. Use A2A endpoint to invoke the agent"
	@echo "   3. View in AWS Console: https://console.aws.amazon.com/bedrock/home?region=$(AWS_REGION)#/agentcore/agents"

status: ## Check agent deployment status
	agentcore status

invoke-local: ## Invoke local agent (use PROMPT="your message" make invoke-local)
	@if [ -z "$(PROMPT)" ]; then \
		echo "🧪 Testing local agent with default prompt..."; \
		agentcore invoke --local '{"prompt": "From: test@example.com - Hi, I need help with my order. Thanks!"}'; \
	else \
		echo "🧪 Testing local agent with custom prompt..."; \
		agentcore invoke --local '{"prompt": "$(PROMPT)"}'; \
	fi

invoke-remote: ## Invoke remote agent (use PROMPT="your message" make invoke-remote)
	agentcore invoke '{"prompt": "$(PROMPT)"}'

logs: ## View agent logs
	@echo "📊 Viewing agent logs..."
	agentcore logs

setup-infra: ## Setup AWS infrastructure (idempotent)
	@echo "🏗️  Setting up AWS infrastructure..."
	./setup-infrastructure.sh

clean: ## Clean up local resources
	@echo "🧹 Cleaning up..."
	pkill -f "agentcore launch --local" || true
	rm -rf .agentcore/

undeploy: check-env ## Delete deployed agent from AWS (use AGENT_NAME=foo for custom name)
	@echo "🗑️  UNDEPLOYING: $(if $(AGENT_NAME),$(AGENT_NAME),Bedrock_Customer_Support_Agent)"
	@echo "💥 What will be deleted:"
	@echo "   • AgentCore runtime and container"
	@echo "   • All associated endpoints"
	@echo "   • Agent networking configuration"
	@echo "   ⚠️  NOTE: IAM roles and ECR images are preserved"
	@echo ""
	@echo "ℹ️  Using direct API calls because AgentCore CLI is broken in preview"
	python undeploy-via-api.py "$(if $(AGENT_NAME),$(AGENT_NAME),Bedrock_Customer_Support_Agent)"
	@echo ""
	@echo "✅ UNDEPLOY COMPLETE!"
	@echo "💡 The agent runtime has been deleted from AWS"
	@echo "🔄 You can run 'make deploy' to create a new agent"

destroy: ## Delete deployed agent from AWS (legacy CLI - may not work)
	@echo "⚠️  Destroying deployed agent..."
	@read -p "Are you sure you want to delete the deployed agent? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	agentcore delete

all: install setup-infra configure deploy status ## Install, setup infra, configure, deploy, and check status

quick-test: ## Quick local test
	make test-local PROMPT="Hello, can you help me with my order?"