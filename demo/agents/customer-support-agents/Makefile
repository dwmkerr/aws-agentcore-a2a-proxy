.DEFAULT_GOAL := help

.PHONY: help
help: # show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: check-env
check-env: # check required environment variables
	@test -n "$(AWS_ACCESS_KEY_ID)" || (echo "Error: AWS_ACCESS_KEY_ID not set" && exit 1)
	@test -n "$(AWS_SECRET_ACCESS_KEY)" || (echo "Error: AWS_SECRET_ACCESS_KEY not set" && exit 1)
	@test -n "$(AWS_REGION)" || (echo "Error: AWS_REGION not set" && exit 1)
	@test -n "$(IAM_ROLE_ARN)" || (echo "Error: IAM_ROLE_ARN not set" && exit 1)
	@test -n "$(ECR_REPOSITORY_URL)" || (echo "Error: ECR_REPOSITORY_URL not set" && exit 1)

.PHONY: build-image
build-image: check-env # build and push container image to ECR
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPOSITORY_URL)
	docker build -t $(ECR_REPOSITORY_URL):latest .
	docker push $(ECR_REPOSITORY_URL):latest

.PHONY: install
install: build-image # build image and deploy agent to AWS
	python deploy-via-api.py "Bedrock_Customer_Support_Agent" $(ECR_REPOSITORY_URL):latest $(IAM_ROLE_ARN)

.PHONY: check-aws-env
check-aws-env: # check minimal AWS environment variables for API calls
	@test -n "$(AWS_ACCESS_KEY_ID)" || (echo "Error: AWS_ACCESS_KEY_ID not set" && exit 1)
	@test -n "$(AWS_SECRET_ACCESS_KEY)" || (echo "Error: AWS_SECRET_ACCESS_KEY not set" && exit 1)
	@test -n "$(AWS_REGION)" || (echo "Error: AWS_REGION not set" && exit 1)

.PHONY: uninstall
uninstall: check-aws-env # remove agent from AWS
	python undeploy-via-api.py "Bedrock_Customer_Support_Agent"

.PHONY: clean
clean: # clean up local resources
	rm -rf .agentcore/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true