# GitHub Development Assistant Agent Makefile

.DEFAULT_GOAL := help
AGENT_NAME := github-dev-assistant
IMAGE_NAME := $(AGENT_NAME)
VERSION := 1.0.0

# Environment variables
OIDC_CLIENT_ID ?= 
OIDC_CLIENT_SECRET ?= 
IAM_ROLE_ARN ?= 
ECR_REPOSITORY_URL ?= 
AWS_REGION ?= us-east-1
GITHUB_TOKEN ?= # Optional: for local testing only

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done


.PHONY: install
install: # install dependencies
	pip install -r requirements.txt

.PHONY: test
test: # run tests
	python -m pytest tests/ -v

.PHONY: run
run: # run agent locally (optionally set GITHUB_TOKEN for testing)
	GITHUB_TOKEN=$(GITHUB_TOKEN) python agent.py

.PHONY: deploy
deploy: install # deploy agent to AWS Bedrock AgentCore
	@if [ -z "$(IAM_ROLE_ARN)" ]; then \
		echo "Error: IAM_ROLE_ARN environment variable is required"; \
		exit 1; \
	fi
	../../scripts/deploy-agent \
		--agent-name "$(AGENT_NAME)" \
		--execution-role-arn $(IAM_ROLE_ARN) \
		--region $(AWS_REGION)

.PHONY: undeploy
undeploy: # remove agent from AWS Bedrock AgentCore
	../../scripts/undeploy-agent --agent-name "$(AGENT_NAME)" --region $(AWS_REGION)

.PHONY: logs
logs: # show agent logs (when deployed)
	aws logs tail /aws/bedrock/agentcore/$(AGENT_NAME) --follow

.PHONY: clean
clean: # clean up local artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
