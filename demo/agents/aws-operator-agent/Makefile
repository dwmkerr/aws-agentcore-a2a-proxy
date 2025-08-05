# AWS Operator Agent Makefile

.DEFAULT_GOAL := help
AGENT_NAME := aws_operator_agent
IMAGE_NAME := $(AGENT_NAME)
IMAGE_TAG ?= latest

# Environment variables
IAM_ROLE_ARN ?= # For deployment (general AgentCore role)
IAM_AGENT_ROLE_ARN ?= # For AWS operations (specific AWS Operator Agent role)
EXECUTION_ROLE_ARN ?= $(IAM_AGENT_ROLE_ARN)
ECR_REPOSITORY_URL ?= 
AWS_REGION ?= us-east-1

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: test
test: # run tests
	python -m pytest tests/ -v

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
	docker push $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(IMAGE_TAG)

.PHONY: install
install: build-image # build image and deploy agent to AWS Bedrock AgentCore
	@if [ -z "$(EXECUTION_ROLE_ARN)" ]; then \
		echo "Error: EXECUTION_ROLE_ARN environment variable is required"; \
		exit 1; \
	fi
	uv run --with boto3==1.40.1 ../../scripts/manage-agent.py deploy \
		--agent-name "$(AGENT_NAME)" \
		--execution-role-arn $(EXECUTION_ROLE_ARN) \
		--region $(AWS_REGION)

.PHONY: uninstall
uninstall: # remove agent from AWS Bedrock AgentCore
	uv run --with boto3==1.40.1 ../../scripts/manage-agent.py delete --agent-name "$(AGENT_NAME)" --region $(AWS_REGION)
