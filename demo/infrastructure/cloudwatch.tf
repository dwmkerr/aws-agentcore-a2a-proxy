# CloudWatch Log Group for Bedrock AgentCore
resource "aws_cloudwatch_log_group" "bedrock_agentcore" {
  name              = "/aws/bedrock/agentcore"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

