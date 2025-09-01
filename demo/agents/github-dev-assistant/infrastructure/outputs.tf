output "github_dev_assistant_role_arn" {
  description = "ARN of the GitHub Development Assistant role"
  value       = aws_iam_role.github_dev_assistant.arn
}

output "github_dev_assistant_role_name" {
  description = "Name of the GitHub Development Assistant role"
  value       = aws_iam_role.github_dev_assistant.name
}