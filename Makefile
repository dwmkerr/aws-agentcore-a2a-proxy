.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

HOST ?= localhost
PORT ?= 2972

.PHONY: dev
dev: # run in development mode
	cd aws-bedrock-a2a-proxy && uv run uvicorn aws_bedrock_a2a_proxy.main:create_app --factory --host $(HOST) --port $(PORT) --reload

.PHONY: test
test: # run tests with coverage
	mkdir -p aws-bedrock-a2a-proxy/artifacts/coverage
	cd aws-bedrock-a2a-proxy && uv run --extra dev pytest tests/ -v --cov=src/aws_bedrock_a2a_proxy --cov-report=term-missing --cov-report=html:artifacts/coverage/html --cov-report=lcov:artifacts/coverage/coverage.lcov

.PHONY: lint
lint: # run linting and type checking
	cd aws-bedrock-a2a-proxy && uv run --extra dev flake8 src/ tests/
	cd aws-bedrock-a2a-proxy && uv run --extra dev pyright src/

.PHONY: lint-fix
lint-fix: # lint and fix the code
	cd aws-bedrock-a2a-proxy && uv run --extra dev black .


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
install-demo-agents: # build and deploy both demo agents using demo infrastructure
	@(cd demo/agents/github-dev-assistant && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	EXECUTION_ROLE_ARN=$$(cd ../../infrastructure && terraform output -raw agentcore_execution_role_arn) \
	make install)
	@(cd demo/agents/aws-operator-agent && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	EXECUTION_ROLE_ARN=$$(cd ../../infrastructure && terraform output -raw aws_operator_agent_role_arn) \
	make install)

.PHONY: uninstall-demo-agents
uninstall-demo-agents: # remove both demo agents from AWS
	@cd demo/agents/github-dev-assistant && make uninstall || true
	@cd demo/agents/aws-operator-agent && make uninstall || true
