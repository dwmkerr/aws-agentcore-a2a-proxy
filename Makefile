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

.PHONY: clean
clean: # clean up build artifacts and cache
	rm -rf aws-bedrock-a2a-proxy/.pytest_cache/
	rm -rf aws-bedrock-a2a-proxy/htmlcov/
	rm -rf aws-bedrock-a2a-proxy/.coverage
	rm -rf aws-bedrock-a2a-proxy/dist/
	rm -rf aws-bedrock-a2a-proxy/build/
	find aws-bedrock-a2a-proxy -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find aws-bedrock-a2a-proxy -type f -name "*.pyc" -delete 2>/dev/null || true