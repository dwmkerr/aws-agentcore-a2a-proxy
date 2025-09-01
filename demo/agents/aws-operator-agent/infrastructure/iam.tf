# Trust policy for AWS Operator Agent (inherits from core)
data "aws_iam_policy_document" "aws_operator_trust" {
  source_policy_documents = [
    data.aws_iam_policy_document.core_trust.json
  ]
}

# Get core trust policy from data source
data "aws_iam_policy_document" "core_trust" {
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

# AWS Operator Agent specific role
resource "aws_iam_role" "aws_operator_agent" {
  name               = "AwsOperatorAgentRole"
  assume_role_policy = data.aws_iam_policy_document.aws_operator_trust.json
  description        = "Execution role for AWS Operator Agent with read-only AWS access"
  tags               = var.tags
}

# Attach AWS managed ReadOnlyAccess policy
resource "aws_iam_role_policy_attachment" "aws_operator_readonly" {
  role       = aws_iam_role.aws_operator_agent.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# Attach core AgentCore execution policy
resource "aws_iam_role_policy_attachment" "aws_operator_execution" {
  role       = aws_iam_role.aws_operator_agent.name
  policy_arn = var.core_execution_policy_arn
}