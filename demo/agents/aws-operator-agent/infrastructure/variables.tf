variable "core_execution_role_arn" {
  description = "ARN of the core AgentCore execution role"
  type        = string
}

variable "core_execution_policy_arn" {
  description = "ARN of the core AgentCore execution policy"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Agent       = "aws-operator"
    Project     = "aws-bedrock-a2a-proxy"
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}