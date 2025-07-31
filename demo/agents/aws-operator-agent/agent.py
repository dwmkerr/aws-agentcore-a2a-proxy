#!/usr/bin/env python3
"""
AWS Operator Agent

A comprehensive AWS operations assistant that provides secure access to AWS services via boto3.
Uses structured tools for reliable AWS operations with role-based access control.

Features:
- Structured tool definitions for all major AWS services
- Role-based access control with region restrictions
- Comprehensive error handling and logging
- Support for OIDC authentication

Integrates with:
- AWS SDK (boto3) for all AWS services
- Strands agent framework for tool orchestration
- AWS IAM for role-based access control
"""

import logging
from typing import Dict, List, Any

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from aws_command_tool import aws_command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the system prompt
SYSTEM_PROMPT = """
You are an AWS Operator Assistant with access to comprehensive AWS CLI capabilities.

**Your Role:**
- Execute any AWS CLI command or boto3 operation across ALL AWS services
- Give clear, actionable responses with proper error handling

**Available AWS Services:**
You have access to ALL AWS services through the aws_command tool including:
- **S3**: Buckets, objects, lifecycle, permissions
- **EC2**: Instances, volumes, snapshots, security groups, VPCs
- **Lambda**: Functions, layers, event sources, aliases
- **RDS**: Databases, clusters, snapshots, parameter groups
- **IAM**: Users, roles, policies, groups, access keys
- **CloudFormation**: Stacks, templates, changesets
- **SNS**: Topics, subscriptions, messages
- **SQS**: Queues, messages, dead letter queues
- **CloudWatch**: Metrics, logs, alarms, dashboards
- **Route53**: DNS, hosted zones, health checks
- **ELB**: Load balancers, target groups, listeners
- **Auto Scaling**: Groups, policies, launch configurations
- **And 200+ other AWS services**

**Guidelines:**
- Use the aws_command tool for ALL AWS operations
- Support both natural language and direct AWS CLI commands
- Provide summaries with key insights from command results
- Handle errors gracefully and suggest alternatives when possible

Example queries you can handle:
- "List my S3 buckets" -> aws_command("s3 ls")
- "Show EC2 instances" -> aws_command("ec2 describe-instances")
- "Get Lambda functions" -> aws_command("lambda list-functions")
- "Who am I?" -> aws_command("sts get-caller-identity")
- "List CloudFormation stacks" -> aws_command("cloudformation list-stacks")
- "Show CloudWatch alarms" -> aws_command("cloudwatch describe-alarms")
- "Describe my VPCs" -> aws_command("ec2 describe-vpcs")
- "List Route53 hosted zones" -> aws_command("route53 list-hosted-zones")
- Direct CLI: aws_command("ec2 describe-instances --region us-west-2")
- Direct CLI: aws_command("s3 ls s3://my-bucket")
"""

# Create the agent with all tools
app = BedrockAgentCoreApp()

model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)

# Define all available tools - now just one comprehensive tool
aws_tools = [
    aws_command
]

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=aws_tools
)

def get_agent_tools() -> List[Dict[str, Any]]:
    """Get list of available tools for auto-discovery by A2A proxy"""
    tools_info = []
    
    for tool_func in aws_tools:
        # Extract tool information from the function
        tool_name = tool_func.__name__
        tool_doc = tool_func.__doc__ or "No description available"
        
        # Parse the docstring to extract description and examples
        lines = [line.strip() for line in tool_doc.strip().split('\n') if line.strip()]
        description = lines[0] if lines else "AWS command execution tool"
        
        # Extract examples from docstring only
        examples = []
        in_examples = False
        for line in lines:
            if "Examples:" in line or "examples:" in line:
                in_examples = True
                continue
            if in_examples and line.startswith('- "'):
                # Extract example from quoted string
                example = line.strip('- "').rstrip('"')
                examples.append(example)
        
        tools_info.append({
            "id": tool_name,
            "name": tool_name.replace('_', ' ').title(),
            "description": description,
            "examples": examples,
            "tags": ["aws", "cli", "boto3", "infrastructure", "operations", "all-services"]
        })
    
    return tools_info

@app.entrypoint
def invoke(payload):
    """AgentCore entrypoint for processing requests"""
    logger.info(f"AgentCore invoke called with payload keys: {list(payload.keys())}")
    
    try:
        user_message = payload.get("prompt", "Hello! What AWS operation would you like to perform?")
        logger.info(f"Extracted user message: '{user_message}'")
        logger.info(f"Available tools: {[tool.__name__ for tool in aws_tools]}")
        
        result = agent(user_message)
        logger.info(f"Generated response length: {len(result.message) if result.message else 0}")
        logger.info(f"Agent result type: {type(result)}")
        
        return {"result": result.message}
    except Exception as e:
        logger.error(f"Error in AgentCore entrypoint: {str(e)}", exc_info=True)
        return {"result": f"❌ AgentCore error: {str(e)}"}

if __name__ == "__main__":
    # For local testing
    app.run()