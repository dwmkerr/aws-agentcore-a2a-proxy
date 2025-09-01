variable "core_execution_role_arn" {
  description = "ARN of the core AgentCore execution role"
  type        = string
}

variable "core_execution_policy_arn" {
  description = "ARN of the core AgentCore execution policy"
  type        = string
}

variable "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  type        = string
}

variable "github_repo_owner" {
  description = "GitHub repository owner for OIDC trust relationship"
  type        = string
  default     = "dwmkerr"
}

variable "github_repo_name" {
  description = "GitHub repository name for OIDC trust relationship"
  type        = string
  default     = "aws-bedrock-a2a-proxy"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Agent       = "github-dev-assistant"
    Project     = "aws-bedrock-a2a-proxy"
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}