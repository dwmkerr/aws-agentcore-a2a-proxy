variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "role_name" {
  description = "Name of the IAM role for AgentCore execution"
  type        = string
  default     = "AgentCoreExecutionRole"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID to enable access for"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days"
  type        = number
  default     = 14
}

variable "enable_bedrock_logging" {
  description = "Enable Bedrock model invocation logging"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "aws-bedrock-a2a-proxy"
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}