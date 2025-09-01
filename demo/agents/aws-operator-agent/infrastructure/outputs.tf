output "aws_operator_agent_role_arn" {
  description = "ARN of the AWS Operator Agent role"
  value       = aws_iam_role.aws_operator_agent.arn
}

output "aws_operator_agent_role_name" {
  description = "Name of the AWS Operator Agent role"
  value       = aws_iam_role.aws_operator_agent.name
}