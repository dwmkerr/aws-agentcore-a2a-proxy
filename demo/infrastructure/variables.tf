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

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "aws-bedrock-a2a-proxy"
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}