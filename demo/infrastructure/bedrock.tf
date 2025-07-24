# Get information about the Bedrock model
data "aws_bedrock_foundation_model" "selected" {
  model_id = var.bedrock_model_id
}

# Request model access (this creates a request that may need approval)
resource "aws_bedrock_model_invocation_logging_configuration" "model_access" {
  count = var.enable_bedrock_logging ? 1 : 0
  
  logging_config {
    embedding_data_delivery_enabled = false
    image_data_delivery_enabled     = false
    text_data_delivery_enabled      = true

    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.bedrock_agentcore.name
      role_arn       = aws_iam_role.agentcore_execution.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.bedrock_agentcore,
    aws_iam_role.agentcore_execution
  ]
}