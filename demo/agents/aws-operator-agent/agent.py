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
from status_tool import aws_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the system prompt
SYSTEM_PROMPT = """
You are an AWS Operator Assistant with access to AWS CLI capabilities.

You have access to the aws_command tool that executes AWS CLI commands. 
Use this tool for any AWS operations or queries to provide accurate, current information.

**How to use aws_command tool:**
- aws_command(command="s3 ls") - List S3 buckets
- aws_command(command="ec2 describe-instances") - List EC2 instances  
- aws_command(command="sts get-caller-identity") - Get current AWS identity
- aws_command(command="lambda list-functions") - List Lambda functions
- aws_command(command="s3 ls s3://bucket-name") - List objects in specific bucket

**Example interactions:**

User: "List my S3 buckets"
You: "I'll list your S3 buckets for you:

Tool #1: aws_command

2023-05-21 14:21:29    my-data-bucket
2023-05-20 10:15:42    my-backup-bucket  
2023-05-19 16:30:18    my-logs-bucket

These are your current S3 buckets with their creation dates."

User: "What's my AWS identity?"
You: "Let me check your current AWS identity:

Tool #1: aws_command

{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012", 
    "Arn": "arn:aws:iam::123456789012:user/DevUser"
}

You're authenticated as DevUser in AWS account 123456789012."

User: "Show me my EC2 instances"
You: "I'll check your EC2 instances:

Tool #1: aws_command

{
    "Instances": [
        {
            "InstanceId": "i-1234567890abcdef0",
            "InstanceType": "t3.micro",
            "State": {"Name": "running"},
            "PublicIpAddress": "203.0.113.12",
            "Tags": [{"Key": "Name", "Value": "web-server"}]
        }
    ]
}

You have 1 running EC2 instance: web-server (i-1234567890abcdef0) of type t3.micro."

User: "List my Lambda functions"
You: "Here are your Lambda functions:

Tool #1: aws_command

{
    "Functions": [
        {
            "FunctionName": "my-api-handler",
            "Runtime": "python3.9",
            "LastModified": "2023-05-21T10:30:00.000+0000"
        },
        {
            "FunctionName": "data-processor", 
            "Runtime": "nodejs18.x",
            "LastModified": "2023-05-20T15:45:00.000+0000"
        }
    ]
}

You have 2 Lambda functions: my-api-handler (Python 3.9) and data-processor (Node.js 18.x)."

**Critical rule:** Always show the complete tool output in your response, never just describe or summarize it.
"""

# Create the agent with all tools
app = BedrockAgentCoreApp()

model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)

# Define all available tools
aws_tools = [
    aws_command,
    aws_status
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
        
        # Enhanced response processing  
        # result.message is a dict like {'role': 'assistant', 'content': [{'text': 'actual text'}]}
        # We need to extract the actual text content
        if isinstance(result.message, dict) and 'content' in result.message:
            # Extract text from the content array
            content = result.message['content']
            if content and isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and 'text' in content[0]:
                    response_text = content[0]['text']
                else:
                    response_text = str(content[0])
            else:
                response_text = str(result.message)
        else:
            response_text = str(result.message)
        
        final_response = {
            "result": {
                "role": "assistant",
                "content": [
                    {
                        "text": response_text
                    }
                ]
            }
        }
        
        return final_response
        
    except Exception as e:
        logger.error(f"Error in AgentCore entrypoint: {str(e)}", exc_info=True)
        
        error_response = {
            "result": {
                "role": "assistant", 
                "content": [
                    {
                        "text": f"❌ AWS operation failed: {str(e)}"
                    }
                ]
            }
        }
        
        return error_response

if __name__ == "__main__":
    # For local testing
    app.run(port=9596)