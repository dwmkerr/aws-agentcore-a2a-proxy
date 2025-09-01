#!/usr/bin/env python3
"""
AWS Operator Agent

A generic tool-enumeration agent that discovers available AWS tools
and lets the LLM decide which tools to use based on user requests.
"""

import json
import logging
import inspect
import boto3
from typing import Dict, List, Any, Callable
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Import available tools
from aws_command_tool import aws_command
from status_tool import aws_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GenericToolAgent:
    """Generic agent that enumerates available tools and lets LLM decide which to use"""
    
    def __init__(self):
        self.bedrock_client = None
        self.available_tools = {}
        self._discover_tools()
        
    def _discover_tools(self):
        """Discover all available tools"""
        # Import all available tool functions
        tool_functions = {
            'aws_command': aws_command,
            'aws_status': aws_status
        }
        
        for name, func in tool_functions.items():
            try:
                # Get function signature and docstring
                sig = inspect.signature(func)
                doc = inspect.getdoc(func) or "No description available"
                
                # Build parameter schema
                parameters = {}
                for param_name, param in sig.parameters.items():
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
                    param_info = {
                        "type": self._python_type_to_json_type(param_type),
                        "required": param.default == inspect.Parameter.empty
                    }
                    parameters[param_name] = param_info
                
                self.available_tools[name] = {
                    "name": name,
                    "description": doc,
                    "function": func,
                    "parameters": parameters
                }
                
            except Exception as e:
                logger.error(f"Failed to inspect tool {name}: {e}")
        
        logger.info(f"Discovered {len(self.available_tools)} tools: {list(self.available_tools.keys())}")
    
    def _python_type_to_json_type(self, python_type):
        """Convert Python type to JSON schema type"""
        if python_type == str:
            return "string"
        elif python_type == int:
            return "integer"
        elif python_type == float:
            return "number"
        elif python_type == bool:
            return "boolean"
        elif python_type == list:
            return "array"
        elif python_type == dict:
            return "object"
        else:
            return "string"  # Default fallback
            
    def _get_bedrock_client(self):
        """Get or create Bedrock client"""
        if not self.bedrock_client:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        return self.bedrock_client
        
    def _create_system_prompt(self) -> str:
        """Create system prompt with available tools"""
        if not self.available_tools:
            return "You are a helpful AWS assistant. However, no tools are currently available."
            
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.available_tools.values()
        ])
        
        tools_schemas = {
            name: {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for name, tool in self.available_tools.items()
        }
        
        return f"""You are an AWS operations assistant with access to the following tools:

{tools_description}

You can call these tools to help users with AWS operations. When you need to use a tool, respond with a JSON object containing:
- "tool_call": true
- "tool_name": the name of the tool to call
- "arguments": the arguments to pass to the tool

When you have the information needed to answer the user's question, respond normally without tool calls.

Available tools and their schemas:
{json.dumps(tools_schemas, indent=2)}

Always be helpful and provide clear explanations of AWS resources and operations.
"""
    
    async def handle_request(self, prompt: str) -> str:
        """Main entry point for handling user requests"""
        system_prompt = self._create_system_prompt()
        return await self._conversation_loop(system_prompt, prompt)
    
    async def _conversation_loop(self, system_prompt: str, user_prompt: str, max_iterations: int = 5) -> str:
        """Handle conversation with tool calling"""
        bedrock = self._get_bedrock_client()
        
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        for iteration in range(max_iterations):
            try:
                # Call LLM
                response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4000,
                        "system": system_prompt,
                        "messages": messages
                    })
                )
                
                response_body = json.loads(response['body'].read())
                assistant_message = response_body['content'][0]['text']
                
                # Check if LLM wants to call a tool
                try:
                    tool_request = json.loads(assistant_message)
                    if tool_request.get('tool_call'):
                        tool_name = tool_request.get('tool_name')
                        arguments = tool_request.get('arguments', {})
                        
                        logger.info(f"LLM requesting tool call: {tool_name} with args: {arguments}")
                        
                        # Call the tool
                        if tool_name in self.available_tools:
                            tool_func = self.available_tools[tool_name]['function']
                            try:
                                # Call the tool function with arguments
                                if arguments:
                                    tool_result = tool_func(**arguments)
                                else:
                                    tool_result = tool_func()
                                    
                                # Convert result to string if needed
                                if not isinstance(tool_result, str):
                                    tool_result = json.dumps(tool_result, indent=2)
                                    
                            except Exception as e:
                                tool_result = f"Error calling tool {tool_name}: {str(e)}"
                                logger.error(f"Tool execution error: {e}")
                        else:
                            tool_result = f"Tool {tool_name} not found in available tools"
                        
                        # Add tool result to conversation
                        messages.append({"role": "assistant", "content": assistant_message})
                        messages.append({"role": "user", "content": f"Tool result: {tool_result}"})
                        
                        continue  # Continue conversation loop
                        
                except json.JSONDecodeError:
                    # Not a tool call, this is the final response
                    return assistant_message
                    
                return assistant_message
                
            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                return f"Sorry, I encountered an error: {str(e)}"
        
        return "I've reached the maximum number of tool calls. Please try a simpler request."

# Create agent instance
agent = GenericToolAgent()

# Create BedrockAgentCoreApp with the agent
app = BedrockAgentCoreApp()

@app.agent
async def aws_operator_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """AWS Operator Agent entry point"""
    logger.info(f"Received payload: {json.dumps(payload, default=str)}")
    
    # Extract user message
    user_message = payload.get("prompt", "Hello, what AWS operations can you help me with?")
    
    try:
        # Process the request
        response = await agent.handle_request(user_message)
        return {"result": response}
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {"result": f"Sorry, I encountered an error: {str(e)}"}

# Test function for local development
async def test_agent():
    """Test the agent locally"""
    test_queries = [
        "What tools are available to me?",
        "Check my AWS status", 
        "List my S3 buckets",
        "Show me my current AWS identity",
        "List my EC2 instances"
    ]
    
    print("=== AWS Operator Agent Test ===")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            response = await agent.handle_request(query)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())