# Get information about the Bedrock model
data "aws_bedrock_foundation_model" "selected" {
  model_id = var.bedrock_model_id
}

# Bedrock model invocation logging configuration
resource "aws_bedrock_model_invocation_logging_configuration" "agentcore" {
  count = var.enable_bedrock_logging && var.create_cloudwatch_logs ? 1 : 0
  
  logging_config {
    embedding_data_delivery_enabled = false
    image_data_delivery_enabled     = false
    text_data_delivery_enabled      = true

    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.bedrock_agentcore[0].name
      role_arn       = aws_iam_role.agentcore_execution.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.bedrock_agentcore,
    aws_iam_role.agentcore_execution,
    aws_iam_role_policy_attachment.agentcore_execution
  ]
}