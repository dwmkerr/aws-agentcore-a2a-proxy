# CloudWatch Log Group for Bedrock AgentCore
resource "aws_cloudwatch_log_group" "bedrock_agentcore" {
  count = var.create_cloudwatch_logs ? 1 : 0
  
  name              = "/aws/bedrock/agentcore"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

