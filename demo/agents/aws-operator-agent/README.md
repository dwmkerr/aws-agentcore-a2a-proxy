# AWS Operator Agent

A general-purpose AWS operations assistant that provides natural language access to AWS services via boto3. This agent can handle any AWS operation through conversational prompts.

## Features

- **Universal AWS Access**: Supports any AWS service and operation through boto3
- **Natural Language Processing**: Converts conversational prompts to AWS API calls
- **Role-Based Access Control**: OIDC integration with user roles (readonly, operator, admin)
- **Smart Response Formatting**: Provides human-readable summaries with detailed JSON when needed
- **Region Support**: Automatic region detection from prompts
- **Comprehensive Error Handling**: Clear error messages and logging

## Example Prompts

### S3 Operations
```
"List my S3 buckets"
"Show me my S3 storage"
```

### EC2 Operations  
```
"Show EC2 instances"
"List instances in us-west-2"
"Show my servers"
```

### Lambda Operations
```
"Get my Lambda functions" 
"Show Lambda functions"
"List serverless functions"
```

### RDS Operations
```
"Show RDS databases"
"List my databases"
"Get DB instances"
```

### Identity & Access
```
"Who am I?"
"Show my AWS identity"
"Get caller identity"
```

### CloudFormation
```
"List CloudFormation stacks"
"Show my stacks"
```

### IAM Operations
```
"List IAM users"
"Show users"
```

### CloudWatch
```
"Show CloudWatch alarms"
"List alarms"
"Get monitoring alerts"
```

### Other Services
```
"List SNS topics"
"Show SQS queues"  
"Get ElastiCache clusters"
```

## How It Works

1. **Natural Language Parsing**: The agent analyzes your prompt to identify:
   - AWS service (S3, EC2, Lambda, etc.)
   - Operation (list, describe, get, etc.)
   - Parameters (region, filters, etc.)

2. **Dynamic boto3 Calls**: Creates appropriate boto3 clients and executes the requested operations

3. **Response Formatting**: Converts AWS API responses to user-friendly summaries with optional detailed JSON

## Supported Services

The agent can work with any AWS service that has boto3 support, including:

- **Compute**: EC2, Lambda, ECS, Fargate
- **Storage**: S3, EBS, EFS
- **Databases**: RDS, DynamoDB, ElastiCache
- **Networking**: VPC, Route53, CloudFront  
- **Security**: IAM, STS, KMS
- **Management**: CloudFormation, CloudWatch, CloudTrail
- **Application Integration**: SNS, SQS, EventBridge
- **And many more...**

## Access Control

The agent respects role-based permissions:

- **readonly**: Can view resources but not modify
- **operator**: Can perform common operations
- **admin**: Full access to all operations

User roles are determined from OIDC claims based on group membership.

## Region Support

The agent automatically detects regions mentioned in prompts:
- "Show EC2 instances in us-west-2"
- "List S3 buckets in eu-central-1"

Default regions can be configured per user.

## Error Handling

The agent provides clear error messages for:
- Invalid AWS operations
- Access denied scenarios
- Service unavailability
- Malformed requests

## Deployment

The agent is deployed as an AWS Bedrock AgentCore service with:
- Docker containerization
- ECR image storage
- IAM role-based execution
- CloudWatch logging

> [!NOTE]
> The demo aws-operator-agent uses the Anthropic model anthropic.claude-3-haiku-20240307-v1 from AWS Bedrock.
> By default, AWS accounts do not always have access to every model.
> To get access to models, see [https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html).


## Testing

Test the agent locally:
```bash
make run
```

Or deploy and test via the proxy:
```bash
curl -X POST "http://localhost:2972/agentcore/agents/aws_operator_agent-{ID}/invoke" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List my S3 buckets"}'
```

## Architecture

```
User Prompt → Natural Language Parser → boto3 Client → AWS API → Response Formatter → User
```

The agent maintains no state between requests and relies on AWS IAM roles for authentication and authorization.
