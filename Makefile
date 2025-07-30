.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: dev
dev: # run in development mode
	cd aws-bedrock-a2a-proxy && uv run uvicorn aws_bedrock_a2a_proxy.main:app --host localhost --port 2972 --reload

.PHONY: test
test: # run tests with coverage
	mkdir -p aws-bedrock-a2a-proxy/artifacts/coverage
	cd aws-bedrock-a2a-proxy && uv run pytest tests/ -v --cov=src/aws_bedrock_a2a_proxy --cov-report=term-missing --cov-report=html:artifacts/coverage/html --cov-report=lcov:artifacts/coverage/coverage.lcov

.PHONY: lint
lint: # run linting and type checking
	cd aws-bedrock-a2a-proxy && uv run flake8 src/ tests/
	cd aws-bedrock-a2a-proxy && uv run pyright src/

.PHONY: lint-fix
lint-fix: # lint and fix the code
	cd aws-bedrock-a2a-proxy && uv run black .

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
	@echo "🏗️  Building GitHub Development Assistant image..."
	(cd demo/agents/github-dev-assistant && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make build-image)
	@echo "🏗️  Building AWS Operator Agent image..."
	(cd demo/agents/aws-operator-agent && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make build-image)
	@echo "🚀 Deploying GitHub Development Assistant..."
	(cd demo/agents/github-dev-assistant && \
	../../scripts/deploy-agent \
		--agent-name "github_dev_assistant" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw agentcore_execution_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):github_dev_assistant-latest \
		--region us-east-1)
	@echo "🚀 Deploying AWS Operator Agent..."
	(cd demo/agents/aws-operator-agent && \
	../../scripts/deploy-agent \
		--agent-name "aws_operator_agent" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw aws_operator_agent_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):aws_operator_agent-latest \
		--region us-east-1)

.PHONY: uninstall-demo-agents
uninstall-demo-agents: # remove both demo agents from AWS
	@echo "🗑️  Removing GitHub Development Assistant..."
	cd demo/agents/github-dev-assistant && make undeploy || true
	@echo "🗑️  Removing AWS Operator Agent..."
	cd demo/agents/aws-operator-agent && make undeploy || true
