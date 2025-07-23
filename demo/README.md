# AWS Bedrock A2A Proxy Demo

Demo setup for running the AWS Bedrock AgentCore A2A proxy.

## Infrastructure

Sets up required AWS resources using Terraform:
- IAM roles and policies for AgentCore execution
- CloudWatch logs configuration
- Bedrock model access

```bash
cd infrastructure/
terraform init
terraform plan
terraform apply
```

## Usage

```bash
# Set environment variables from Terraform outputs
export IAM_ROLE_ARN=$(terraform output -raw agentcore_execution_role_arn)
export AWS_REGION=$(terraform output -raw aws_region)

# Run the proxy
cd ../aws-bedrock-a2a-proxy/
make dev
```

## Cleanup

```bash
cd infrastructure/
terraform destroy
```