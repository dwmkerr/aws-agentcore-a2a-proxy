# GitHub Dev Assistant specific IAM role
# This role can be assumed by both AgentCore services and GitHub Actions via OIDC

# Trust policy allowing core services and GitHub Actions OIDC
data "aws_iam_policy_document" "github_agent_trust" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }

  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }

  statement {
    effect = "Allow"
    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }
    actions = ["sts:AssumeRole"]
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo_owner}/${var.github_repo_name}:*"]
    }
  }
}

# GitHub Dev Assistant role
resource "aws_iam_role" "github_dev_assistant" {
  name               = "GitHubDevAssistantRole"
  assume_role_policy = data.aws_iam_policy_document.github_agent_trust.json
  description        = "Execution role for GitHub Development Assistant Agent"
  tags               = var.tags
}

# Attach core AgentCore execution policy
resource "aws_iam_role_policy_attachment" "github_agent_execution" {
  role       = aws_iam_role.github_dev_assistant.name
  policy_arn = var.core_execution_policy_arn
}

# GitHub-specific permissions (if needed for GitHub API access beyond MCP)
data "aws_iam_policy_document" "github_agent_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:github/*"
    ]
  }
}

resource "aws_iam_policy" "github_agent_permissions" {
  name        = "GitHubDevAssistantPolicy"
  description = "Additional permissions for GitHub Development Assistant"
  policy      = data.aws_iam_policy_document.github_agent_permissions.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "github_agent_permissions" {
  role       = aws_iam_role.github_dev_assistant.name
  policy_arn = aws_iam_policy.github_agent_permissions.arn
}