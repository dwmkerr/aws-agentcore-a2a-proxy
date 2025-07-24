output "agentcore_execution_role_arn" {
  description = "ARN of the AgentCore execution role"
  value       = aws_iam_role.agentcore_execution.arn
}

output "agentcore_execution_role_name" {
  description = "Name of the AgentCore execution role"
  value       = aws_iam_role.agentcore_execution.name
}

output "agentcore_user_policy_arn" {
  description = "ARN of the AgentCore user policy"
  value       = aws_iam_policy.agentcore_user.arn
}

output "bedrock_log_group_name" {
  description = "Name of the Bedrock CloudWatch log group"
  value       = aws_cloudwatch_log_group.bedrock_agentcore.name
}

output "aws_region" {
  description = "AWS region where resources are created"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "bedrock_model_id" {
  description = "Bedrock model ID configured for use"
  value       = var.bedrock_model_id
}

output "bedrock_model_name" {
  description = "Bedrock model name"
  value       = data.aws_bedrock_foundation_model.selected.model_name
}

output "console_urls" {
  description = "AWS Console URLs for created resources"
  value = {
    iam_role      = "https://console.aws.amazon.com/iam/home?region=${data.aws_region.current.name}#/roles/${aws_iam_role.agentcore_execution.name}"
    log_group     = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.bedrock_agentcore.name, "/", "$252F")}"
    bedrock       = "https://console.aws.amazon.com/bedrock/home?region=${data.aws_region.current.name}"
    bedrock_model = "https://console.aws.amazon.com/bedrock/home?region=${data.aws_region.current.name}#/foundation-models/${var.bedrock_model_id}"
  }
}