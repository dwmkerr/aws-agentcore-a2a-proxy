.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: init
init: # install dependencies
	uv sync --dev

.PHONY: dev
dev: # run in development mode
	uv run python -m aws_bedrock_a2a_proxy

.PHONY: test
test: # run tests with coverage
	uv run pytest tests/ -v --cov=src/aws_bedrock_a2a_proxy --cov-report=term-missing

.PHONY: lint
lint: # run linting and type checking
	uv run ruff check src/ tests/
	uv run mypy src/

.PHONY: format
format: # format code
	uv run ruff format src/ tests/

.PHONY: build
build: # build Python wheel
	uv build

.PHONY: build-docker
build-docker: # build Docker image
	docker build -t aws-bedrock-a2a-proxy:latest .

.PHONY: cicd
cicd: # run the CI/CD workflow locally
	act -P ubuntu-24.04=ghcr.io/catthehacker/ubuntu:act-latest \
		--artifact-server-path $$PWD/.artifacts

.PHONY: clean
clean: # clean up build artifacts and cache
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete