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
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
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