terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# AWS Operator Agent module
module "aws_operator_agent" {
  source = "../agents/aws-operator-agent/infrastructure"
  
  core_execution_role_arn    = aws_iam_role.agentcore_execution.arn
  core_execution_policy_arn  = aws_iam_policy.agentcore_execution.arn
  tags                       = var.tags
}

# GitHub Development Assistant module
module "github_dev_assistant" {
  source = "../agents/github-dev-assistant/infrastructure"
  
  core_execution_role_arn    = aws_iam_role.agentcore_execution.arn
  core_execution_policy_arn  = aws_iam_policy.agentcore_execution.arn
  github_oidc_provider_arn   = aws_iam_openid_connect_provider.github_actions.arn
  github_repo_owner          = var.github_repo_owner
  github_repo_name           = var.github_repo_name
  tags                       = var.tags
}