.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: init
init: # install dependencies
	cd aws-bedrock-a2a-proxy && uv sync --dev

.PHONY: dev
dev: # run in development mode
	cd aws-bedrock-a2a-proxy && uv run python -m aws_bedrock_a2a_proxy

.PHONY: test
test: # run tests with coverage
	cd aws-bedrock-a2a-proxy && uv run pytest tests/ -v --cov=src/aws_bedrock_a2a_proxy --cov-report=term-missing

.PHONY: lint
lint: # run linting and type checking
	cd aws-bedrock-a2a-proxy && uv run ruff check src/ tests/
	cd aws-bedrock-a2a-proxy && uv run mypy src/

.PHONY: format
format: # format code
	cd aws-bedrock-a2a-proxy && uv run ruff format src/ tests/

.PHONY: build
build: # build Python wheel
	cd aws-bedrock-a2a-proxy && uv build

.PHONY: build-docker
build-docker: # build Docker image
	docker build -t aws-bedrock-a2a-proxy:latest .

.PHONY: cicd
cicd: # run the CI/CD workflow locally
	act -P ubuntu-24.04=ghcr.io/catthehacker/ubuntu:act-latest \
		--artifact-server-path $$PWD/.artifacts

.PHONY: install-demo-infrastructure
install-demo-infrastructure: # create demo AWS infrastructure
	cd demo/infrastructure && terraform init && terraform apply

.PHONY: uninstall-demo-infrastructure
uninstall-demo-infrastructure: # destroy demo AWS infrastructure
	cd demo/infrastructure && terraform destroy

.PHONY: install-demo-agents
install-demo-agents: # deploy demo agents using demo infrastructure
	(cd demo/agents/customer-support-agents && \
	IAM_ROLE_ARN=$$(cd ../../infrastructure && terraform output -raw agentcore_execution_role_arn) \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make install)

.PHONY: uninstall-demo-agents
uninstall-demo-agents: # remove demo agents from AWS
	cd demo/agents/customer-support-agents && make uninstall
