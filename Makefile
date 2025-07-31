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
	@echo "\033[1;37minfo:\033[0m initializing Terraform..."
	@cd demo/infrastructure && terraform init
	@echo "\033[1;32m✅\033[0m Terraform initialized"
	@echo "\033[1;37minfo:\033[0m applying infrastructure..."
	@cd demo/infrastructure && terraform apply
	@echo "\033[1;32m✅ Demo infrastructure installed successfully!\033[0m"

.PHONY: uninstall-demo-infrastructure
uninstall-demo-infrastructure: # destroy demo AWS infrastructure
	@echo "\033[1;37minfo:\033[0m destroying infrastructure..."
	@cd demo/infrastructure && terraform destroy
	@echo "\033[1;32m✅ Demo infrastructure uninstalled successfully!\033[0m"

.PHONY: install-demo-agents
install-demo-agents: # build and deploy both demo agents using demo infrastructure
	@echo "\033[1;37minfo:\033[0m building GitHub Development Assistant image..."
	@(cd demo/agents/github-dev-assistant && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make build-image)
	@echo "\033[1;32m✅\033[0m GitHub Development Assistant image built"
	@echo "\033[1;37minfo:\033[0m building AWS Operator Agent image..."
	@(cd demo/agents/aws-operator-agent && \
	ECR_REPOSITORY_URL=$$(cd ../../infrastructure && terraform output -raw ecr_repository_url) \
	make build-image)
	@echo "\033[1;32m✅\033[0m AWS Operator Agent image built"
	@echo "\033[1;37minfo:\033[0m deploying GitHub Development Assistant..."
	@(cd demo/agents/github-dev-assistant && \
	../../scripts/deploy-agent \
		--agent-name "github_dev_assistant" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw agentcore_execution_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):github_dev_assistant-latest \
		--region us-east-1)
	@echo "\033[1;32m✅\033[0m GitHub Development Assistant deployed"
	@echo "\033[1;37minfo:\033[0m deploying AWS Operator Agent..."
	@(cd demo/agents/aws-operator-agent && \
	../../scripts/deploy-agent \
		--agent-name "aws_operator_agent" \
		--execution-role-arn $$(cd ../../infrastructure && terraform output -raw aws_operator_agent_role_arn) \
		--image-uri $$(cd ../../infrastructure && terraform output -raw ecr_repository_url):aws_operator_agent-latest \
		--region us-east-1)
	@echo "\033[1;32m✅\033[0m AWS Operator Agent deployed"
	@echo "\033[1;32m✅ All demo agents installed successfully!\033[0m"

.PHONY: uninstall-demo-agents
uninstall-demo-agents: # remove both demo agents from AWS
	@echo "\033[1;37minfo:\033[0m removing GitHub Development Assistant..."
	@cd demo/agents/github-dev-assistant && make undeploy || true
	@echo "\033[1;32m✅\033[0m GitHub Development Assistant removed"
	@echo "\033[1;37minfo:\033[0m removing AWS Operator Agent..."
	@cd demo/agents/aws-operator-agent && make undeploy || true
	@echo "\033[1;32m✅\033[0m AWS Operator Agent removed"
	@echo "\033[1;32m✅ All demo agents uninstalled successfully!\033[0m"

.PHONY: logs-aws-agent
logs-aws-agent: # view CloudWatch logs for AWS Operator Agent
	@echo "\033[1;37minfo:\033[0m searching for AWS Operator Agent logs..."
	@LOG_GROUPS=$$(aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock-agentcore/runtimes/" --region us-east-1 --query 'logGroups[?contains(logGroupName, `aws_operator_agent`)].logGroupName' --output text 2>/dev/null || echo ""); \
	if [ -z "$$LOG_GROUPS" ]; then \
		echo "\033[1;31merror:\033[0m No AWS agent logs found. Deploy first with 'make install-demo-agents'"; \
		exit 1; \
	fi; \
	LOG_GROUP=$$(echo "$$LOG_GROUPS" | head -1); \
	echo "\033[1;37minfo:\033[0m log group: $$LOG_GROUP"; \
	aws logs tail "$$LOG_GROUP" --follow --region us-east-1

.PHONY: logs-github-agent  
logs-github-agent: # view CloudWatch logs for GitHub Development Assistant
	@echo "\033[1;37minfo:\033[0m searching for GitHub Development Assistant logs..."
	@LOG_GROUPS=$$(aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock-agentcore/runtimes/" --region us-east-1 --query 'logGroups[?contains(logGroupName, `github_dev_assistant`)].logGroupName' --output text 2>/dev/null || echo ""); \
	if [ -z "$$LOG_GROUPS" ]; then \
		echo "\033[1;31merror:\033[0m No GitHub agent logs found. Deploy first with 'make install-demo-agents'"; \
		exit 1; \
	fi; \
	LOG_GROUP=$$(echo "$$LOG_GROUPS" | head -1); \
	echo "\033[1;37minfo:\033[0m log group: $$LOG_GROUP"; \
	aws logs tail "$$LOG_GROUP" --follow --region us-east-1

.PHONY: test-aws-agent-local
test-aws-agent-local: # test AWS Operator Agent container locally
	@echo "\033[1;37minfo:\033[0m building AWS Operator Agent for local testing..."
	@cd demo/agents/aws-operator-agent && docker build -t aws-operator-agent:local .
	@echo "\033[1;32m✅\033[0m container built"
	@echo "\033[1;37minfo:\033[0m starting container on port 8080..."
	@echo "\033[1;37minfo:\033[0m test with: curl -X POST http://localhost:8080/invocations -H 'Content-Type: application/json' -d '{\"prompt\": \"list my s3 buckets\"}'"
	@docker run -p 8080:8080 --rm aws-operator-agent:local

.PHONY: test-github-agent-local
test-github-agent-local: # test GitHub Development Assistant container locally  
	@echo "\033[1;37minfo:\033[0m building GitHub Development Assistant for local testing..."
	@cd demo/agents/github-dev-assistant && docker build -t github-dev-assistant:local .
	@echo "\033[1;32m✅\033[0m container built"
	@echo "\033[1;37minfo:\033[0m starting container on port 8080..."
	@echo "\033[1;37minfo:\033[0m test with: curl -X POST http://localhost:8080/invocations -H 'Content-Type: application/json' -d '{\"prompt\": \"hello\"}'"
	@docker run -p 8080:8080 --rm github-dev-assistant:local
