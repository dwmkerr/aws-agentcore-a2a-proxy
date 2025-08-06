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

output "aws_operator_agent_role_arn" {
  description = "ARN of the AWS Operator Agent role"
  value       = aws_iam_role.aws_operator_agent.arn
}

output "aws_operator_agent_role_name" {
  description = "Name of the AWS Operator Agent role"
  value       = aws_iam_role.aws_operator_agent.name
}

output "bedrock_log_group_name" {
  description = "Name of the Bedrock CloudWatch log group"
  value       = var.create_cloudwatch_logs ? aws_cloudwatch_log_group.bedrock_agentcore[0].name : null
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

output "ecr_repository_url" {
  description = "ECR repository URL for AgentCore container images"
  value       = aws_ecr_repository.agentcore_agents.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name"
  value       = aws_ecr_repository.agentcore_agents.name
}

output "console_urls" {
  description = "AWS Console URLs for created resources"
  value = {
    iam_role      = "https://console.aws.amazon.com/iam/home?region=${data.aws_region.current.name}#/roles/${aws_iam_role.agentcore_execution.name}"
    log_group     = var.create_cloudwatch_logs ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.bedrock_agentcore[0].name, "/", "$252F")}" : null
    bedrock       = "https://console.aws.amazon.com/bedrock/home?region=${data.aws_region.current.name}"
    bedrock_model = "https://console.aws.amazon.com/bedrock/home?region=${data.aws_region.current.name}#/foundation-models/${var.bedrock_model_id}"
    ecr_repo      = "https://console.aws.amazon.com/ecr/repositories/private/${data.aws_caller_identity.current.account_id}/${aws_ecr_repository.agentcore_agents.name}?region=${data.aws_region.current.name}"
  }
}