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

**Simple Rule:**
- When the user asks you to perform an operation or execute a command, use the aws_command tool
- For everything else (explanations, concepts, help), answer directly

**Examples:**
- "List my S3 buckets" → Use aws_command tool
- "What is S3?" → Answer directly
- "Show EC2 instances" → Use aws_command tool  
- "How do I create a bucket?" → Answer directly
- "Check my identity" → Use aws_command tool
- "What's the difference between EBS and S3?" → Answer directly

Use tools for doing, answer directly for explaining.
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
        
        # Process the result to emphasize actions taken
        response = result.message
        if hasattr(result, 'tool_calls') and result.tool_calls:
            response = f"✅ Executed AWS command. {response}"
        
        return {"result": response}
    except Exception as e:
        logger.error(f"Error in AgentCore entrypoint: {str(e)}", exc_info=True)
        return {"result": f"❌ Execution failed: {str(e)}"}

if __name__ == "__main__":
    # For local testing
    app.run()