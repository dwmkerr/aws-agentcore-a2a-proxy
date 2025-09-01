# GitHub OIDC provider for GitHub Actions
resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = ["sts.amazonaws.com"]
  
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]
  
  tags = var.tags
}

# Trust policy for AgentCore execution role
data "aws_iam_policy_document" "agentcore_trust" {
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
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
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

# Permissions policy for AgentCore execution role
data "aws_iam_policy_document" "agentcore_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:GetFoundationModel",
      "bedrock:ListFoundationModels"
    ]
    resources = [
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/${var.bedrock_model_id}",
      "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock/agentcore*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock/agentcore*:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = ["bedrock-agentcore:*"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchCheckLayerAvailability"
    ]
    resources = ["*"]
  }
}

# User policy for AgentCore invocation
data "aws_iam_policy_document" "agentcore_user" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeAgentRuntime",
      "bedrock-agentcore:ListAgentRuntimes",
      "bedrock-agentcore:DescribeAgentRuntime"
    ]
    resources = ["*"]
  }
}

# AgentCore execution role
resource "aws_iam_role" "agentcore_execution" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.agentcore_trust.json
  description        = "Execution role for AgentCore agents"
  tags               = var.tags
}

# AgentCore execution policy
resource "aws_iam_policy" "agentcore_execution" {
  name        = "${var.role_name}Policy"
  description = "Permissions for AgentCore agent execution"
  policy      = data.aws_iam_policy_document.agentcore_permissions.json
  tags        = var.tags
}

# Attach execution policy to role
resource "aws_iam_role_policy_attachment" "agentcore_execution" {
  role       = aws_iam_role.agentcore_execution.name
  policy_arn = aws_iam_policy.agentcore_execution.arn
}

# User policy for AgentCore operations
resource "aws_iam_policy" "agentcore_user" {
  name        = "AgentCoreUserPolicy"
  description = "Allows user to invoke AgentCore agents"
  policy      = data.aws_iam_policy_document.agentcore_user.json
  tags        = var.tags
}

