# GitHub Development Assistant Agent Makefile

.DEFAULT_GOAL := help
AGENT_NAME := github-dev-assistant
IMAGE_NAME := $(AGENT_NAME)
VERSION := 1.0.0

# Environment variables
GITHUB_TOKEN ?= 
OIDC_CLIENT_ID ?= 
OIDC_CLIENT_SECRET ?= 
IAM_ROLE_ARN ?= 
ECR_REPOSITORY_URL ?= 
AWS_REGION ?= us-east-1

.PHONY: help
help: ## Show this help message
	@echo "GitHub Development Assistant Agent"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	pip install -r requirements.txt

.PHONY: test
test: ## Run tests
	python -m pytest tests/ -v

.PHONY: run
run: ## Run agent locally
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN environment variable is required"; \
		exit 1; \
	fi
	GITHUB_TOKEN=$(GITHUB_TOKEN) python agent.py

.PHONY: deploy
deploy: install ## Deploy agent to AWS Bedrock AgentCore
	@if [ -z "$(IAM_ROLE_ARN)" ]; then \
		echo "Error: IAM_ROLE_ARN environment variable is required"; \
		exit 1; \
	fi
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN environment variable is required"; \
		exit 1; \
	fi
	python deploy-via-api.py \
		--execution-role-arn $(IAM_ROLE_ARN) \
		--agent-name "$(AGENT_NAME)" \
		--github-token $(GITHUB_TOKEN) \
		--oidc-client-id $(OIDC_CLIENT_ID)

.PHONY: undeploy
undeploy: ## Remove agent from AWS Bedrock AgentCore
	python undeploy-via-api.py --agent-name "$(AGENT_NAME)"

.PHONY: logs
logs: ## Show agent logs (when deployed)
	aws logs tail /aws/bedrock/agentcore/$(AGENT_NAME) --follow

.PHONY: clean
clean: ## Clean up local artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

.PHONY: validate
validate: ## Validate agent configuration
	python -c "import json; json.load(open('config.json')); print('✅ Configuration is valid')"
	python -c "import agent; print('✅ Agent code is valid')"

.PHONY: example
example: ## Show example usage
	@echo "Example usage:"
	@echo ""
	@echo "1. Set required environment variables:"
	@echo "   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx"
	@echo "   export OIDC_CLIENT_ID=your-oidc-client-id"
	@echo "   export IAM_ROLE_ARN=arn:aws:iam::123456789012:role/AgentCoreExecutionRole"
	@echo ""
	@echo "2. Deploy the agent:"
	@echo "   make deploy"
	@echo ""
	@echo "3. Test locally:"
	@echo "   make run"