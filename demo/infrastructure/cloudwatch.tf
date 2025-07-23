# CloudWatch Log Group for Bedrock AgentCore
resource "aws_cloudwatch_log_group" "bedrock_agentcore" {
  name              = "/aws/bedrock/agentcore"
  retention_in_days = 14
  tags              = var.tags
}

# Bedrock model invocation logging configuration
resource "aws_bedrock_model_invocation_logging_configuration" "agentcore" {
  logging_config {
    embedding_data_delivery_enabled = false
    image_data_delivery_enabled     = false
    text_data_delivery_enabled      = true

    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.bedrock_agentcore.name
      role_arn       = aws_iam_role.agentcore_execution.arn
    }
  }
}