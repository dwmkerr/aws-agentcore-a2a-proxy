.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: dev
dev: # run in development mode
	cd aws-bedrock-a2a-proxy && uv run uvicorn aws_bedrock_a2a_proxy.main:create_app --factory --host $${HOST:-localhost} --port $${PORT:-2972} --reload

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
	make build-image)
	@(cd demo/agents/aws-operator-agent && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make build-image)
	@(cd demo/agents/github-dev-assistant && \
	../../scripts/deploy-agent \
		--agent-name "github_dev_assistant" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw agentcore_execution_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):github_dev_assistant-latest \
		--region us-east-1 \
		--description "GitHub development assistant that helps with repository management, code analysis, and development workflows")
	@(cd demo/agents/aws-operator-agent && \
	../../scripts/deploy-agent \
		--agent-name "aws_operator_agent" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw aws_operator_agent_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):aws_operator_agent-latest \
		--region us-east-1 \
		--description "AWS operations agent that manages cloud resources including S3 buckets, EC2 instances, and other AWS services" \
		--skills '[{"id":"aws_operations","name":"AWS Operations","description":"Manage AWS cloud resources including S3 buckets, EC2 instances, and other AWS services using the AWS APIs","tags":["aws","cloud","management"]}]')
	@echo "\033[1;32m✅ All demo agents installed successfully!\033[0m"

.PHONY: uninstall-demo-agents
uninstall-demo-agents: # remove both demo agents from AWS
	@cd demo/agents/github-dev-assistant && make undeploy || true
	@cd demo/agents/aws-operator-agent && make undeploy || true
	@echo "\033[1;32m✅ All demo agents uninstalled successfully!\033[0m"

.PHONY: logs-aws-agent
logs-aws-agent: # view CloudWatch logs for AWS Operator Agent
	@LOG_GROUPS=$$(aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock-agentcore/runtimes/" --region us-east-1 --query 'logGroups[?contains(logGroupName, `aws_operator_agent`)].logGroupName' --output text 2>/dev/null || echo ""); \
	if [ -z "$$LOG_GROUPS" ]; then \
		echo "\033[1;31merror:\033[0m No AWS agent logs found. Deploy first with 'make install-demo-agents'"; \
		exit 1; \
	fi; \
	LOG_GROUP=$$(echo "$$LOG_GROUPS" | head -1); \
	echo "\033[1;37minfo:\033[0m tailing $$LOG_GROUP"; \
	aws logs tail "$$LOG_GROUP" --follow --region us-east-1

.PHONY: logs-github-agent  
logs-github-agent: # view CloudWatch logs for GitHub Development Assistant
	@LOG_GROUPS=$$(aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock-agentcore/runtimes/" --region us-east-1 --query 'logGroups[?contains(logGroupName, `github_dev_assistant`)].logGroupName' --output text 2>/dev/null || echo ""); \
	if [ -z "$$LOG_GROUPS" ]; then \
		echo "\033[1;31merror:\033[0m No GitHub agent logs found. Deploy first with 'make install-demo-agents'"; \
		exit 1; \
	fi; \
	LOG_GROUP=$$(echo "$$LOG_GROUPS" | head -1); \
	echo "\033[1;37minfo:\033[0m tailing $$LOG_GROUP"; \
	aws logs tail "$$LOG_GROUP" --follow --region us-east-1

.PHONY: test-aws-agent-local
test-aws-agent-local: # test AWS Operator Agent container locally
	@cd demo/agents/aws-operator-agent && docker build -t aws-operator-agent:local .
	@echo "\033[1;37minfo:\033[0m container running on port 2973. Test with:"
	@echo "curl -X POST http://localhost:2973/invocations -H 'Content-Type: application/json' -d '{\"prompt\": \"use the aws_status tool\"}'"
	@docker run -p 2973:8080 --rm \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_SESSION_TOKEN \
		-e AWS_REGION \
		-e AWS_DEFAULT_REGION \
		-e OTEL_TRACES_EXPORTER=none \
		-e OTEL_METRICS_EXPORTER=none \
		-e OTEL_LOGS_EXPORTER=none \
		aws-operator-agent:local

.PHONY: test-github-agent-local
test-github-agent-local: # test GitHub Development Assistant container locally  
	@cd demo/agents/github-dev-assistant && docker build -t github-dev-assistant:local .
	@echo "\033[1;37minfo:\033[0m container running on port 2974. Test with:"
	@echo "curl -X POST http://localhost:2974/invocations -H 'Content-Type: application/json' -d '{\"prompt\": \"hello\"}'"
	@docker run -p 2974:8080 --rm github-dev-assistant:local
