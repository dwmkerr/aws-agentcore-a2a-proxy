# Example Terraform variables file
# Copy to terraform.tfvars and customize as needed

# AWS Configuration
aws_region = "us-east-1"
role_name  = "AgentCoreExecutionRole"

# Bedrock Model Configuration
bedrock_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
# Alternative models:
# bedrock_model_id = "anthropic.claude-3-haiku-20240307-v1:0"    # Cheaper option
# bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"   # Previous version

# Logging Configuration
log_retention_days     = 14    # CloudWatch log retention (1-3653 days)
enable_bedrock_logging = true  # Enable Bedrock model invocation logging

# Resource Tags
tags = {
  Project     = "aws-bedrock-a2a-proxy"
  Environment = "demo"
  Owner       = "your-name"
  CostCenter  = "ai-team"
  ManagedBy   = "terraform"
}