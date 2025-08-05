# AWS Operator Agent Makefile

.DEFAULT_GOAL := help
AGENT_NAME := aws_operator_agent
IMAGE_NAME := $(AGENT_NAME)
VERSION := 1.0.0

# Local development uses timestamped tags, CI/CD uses semver from release manifest
TIMESTAMP := $(shell date +%Y%m%d-%H%M%S)
LOCAL_TAG := latest-$(TIMESTAMP)

# Environment variables
IAM_ROLE_ARN ?= # For deployment (general AgentCore role)
IAM_AGENT_ROLE_ARN ?= # For AWS operations (specific AWS Operator Agent role)
ECR_REPOSITORY_URL ?= 
AWS_REGION ?= us-east-1

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
run: # run agent locally (requires AWS CLI and credentials)
	@command -v aws >/dev/null 2>&1 || { echo "Error: AWS CLI not found. Please install AWS CLI"; exit 1; }
	@aws sts get-caller-identity >/dev/null 2>&1 || { echo "Error: AWS credentials not configured"; exit 1; }
	python agent.py

.PHONY: check-build-env
check-build-env: # check required environment variables for ECR builds only
	@test -n "$(ECR_REPOSITORY_URL)" || (echo "Error: ECR_REPOSITORY_URL not set" && exit 1)

.PHONY: check-deploy-env
check-deploy-env: # check required environment variables for agent deployment
	@test -n "$(IAM_AGENT_ROLE_ARN)" || (echo "Error: IAM_AGENT_ROLE_ARN not set" && exit 1)

.PHONY: build-image
build-image: check-build-env # build and push container image to ECR with timestamped tag
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPOSITORY_URL)
	docker build -t $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(LOCAL_TAG) .
	docker tag $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(LOCAL_TAG) $(ECR_REPOSITORY_URL):$(AGENT_NAME)-latest
	docker push $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(LOCAL_TAG)
	docker push $(ECR_REPOSITORY_URL):$(AGENT_NAME)-latest
	@echo "Built and pushed image with tags:"
	@echo "  - $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(LOCAL_TAG)"
	@echo "  - $(ECR_REPOSITORY_URL):$(AGENT_NAME)-latest"

.PHONY: deploy
deploy: install check-deploy-env # deploy agent to AWS Bedrock AgentCore with specific AWS role
	uv run --with boto3 ../../scripts/manage-agent.py deploy \
		--agent-name "$(AGENT_NAME)" \
		--execution-role-arn $(IAM_AGENT_ROLE_ARN) \
		--region $(AWS_REGION)


.PHONY: undeploy
undeploy: # remove agent from AWS Bedrock AgentCore
	uv run --with boto3 ../../scripts/manage-agent.py delete --agent-name "$(AGENT_NAME)" --region $(AWS_REGION)

.PHONY: logs
logs: # show agent logs (when deployed)
	aws logs tail /aws/bedrock/agentcore/$(AGENT_NAME) --follow

.PHONY: clean
clean: # clean up local artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete