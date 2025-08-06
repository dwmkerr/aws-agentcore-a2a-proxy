# AWS Operator Agent Makefile

.DEFAULT_GOAL := help
AGENT_NAME := aws_operator_agent
IMAGE_NAME := $(AGENT_NAME)
IMAGE_TAG ?= latest

# Environment variables
AWS_OPERATIONS_ROLE_ARN ?= # Role with AgentCore + AWS service permissions
ECR_REPOSITORY_URL ?= 
AWS_REGION ?= us-east-1

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: test
test: # run tests
	python -m pytest tests/ -v

.PHONY: build-image
build-image: # build and push container image to ECR
	@test -n "$(ECR_REPOSITORY_URL)" || (echo "Error: ECR_REPOSITORY_URL not set" && exit 1)
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPOSITORY_URL)
	docker build -t $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(IMAGE_TAG) .
	docker push $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(IMAGE_TAG)

.PHONY: install
install: build-image # build image and deploy agent to AWS Bedrock AgentCore
	@test -n "$(AWS_OPERATIONS_ROLE_ARN)" || (echo "Error: AWS_OPERATIONS_ROLE_ARN not set" && exit 1)
	uv run --with boto3==1.40.1 ../../scripts/manage-agent.py deploy \
		--agent-name "$(AGENT_NAME)" \
		--execution-role-arn $(AWS_OPERATIONS_ROLE_ARN) \
		--image-uri $(ECR_REPOSITORY_URL):$(AGENT_NAME)-$(IMAGE_TAG) \
		--region $(AWS_REGION)

.PHONY: uninstall
uninstall: # remove agent from AWS Bedrock AgentCore
	uv run --with boto3==1.40.1 ../../scripts/manage-agent.py delete --agent-name "$(AGENT_NAME)" --region $(AWS_REGION)
