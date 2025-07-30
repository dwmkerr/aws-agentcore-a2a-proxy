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

# AWS Operator Agent specific role
resource "aws_iam_role" "aws_operator_agent" {
  name               = "AwsOperatorAgentRole"
  assume_role_policy = data.aws_iam_policy_document.agentcore_trust.json
  description        = "Execution role for AWS Operator Agent with read-only AWS access"
  tags               = var.tags
}

# Attach AWS managed ReadOnlyAccess policy to AWS Operator Agent role
resource "aws_iam_role_policy_attachment" "aws_operator_agent_readonly" {
  role       = aws_iam_role.aws_operator_agent.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# Attach basic AgentCore execution policy to AWS Operator Agent role
resource "aws_iam_role_policy_attachment" "aws_operator_agent_execution" {
  role       = aws_iam_role.aws_operator_agent.name
  policy_arn = aws_iam_policy.agentcore_execution.arn
}