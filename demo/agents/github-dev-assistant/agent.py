#!/usr/bin/env python3

"""
GitHub Development Assistant Agent

A generic MCP-to-LLM bridge that dynamically discovers available GitHub tools
and lets the LLM decide which tools to use based on user requests.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx
from fastmcp import Client
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GitHubUser:
    """Represents an authenticated GitHub user"""
    username: str
    email: str = ""
    name: str = ""

class MCPClient:
    """Generic MCP client for any MCP server"""
    
    def __init__(self, server_url: str, auth_token: str = None):
        self.server_url = server_url
        self.auth_token = auth_token
        self.client = None
        self.available_tools = []
        
    def update_token(self, auth_token: str):
        """Update the auth token for API calls"""
        self.auth_token = auth_token
        self.client = None
        
    def _get_client(self) -> Client:
        """Get or create MCP client"""
        if not self.client and self.auth_token:
            self.client = Client(self.server_url)
        return self.client
    
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover all available tools from the MCP server"""
        client = self._get_client()
        if not client:
            return []
        
        try:
            async with client:
                tools = await client.list_tools()
                self.available_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]
                logger.info(f"Discovered {len(self.available_tools)} tools: {[t['name'] for t in self.available_tools]}")
                return self.available_tools
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call any available tool dynamically"""
        client = self._get_client()
        if not client:
            return None
        
        try:
            async with client:
                result = await client.call_tool(tool_name, arguments or {})
                return result.content[0].text if result.content else None
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return None

class GenericMCPAgent:
    """Generic agent that works with any MCP server through LLM tool calling"""
    
    def __init__(self, mcp_server_url: str):
        self.mcp_client = MCPClient(mcp_server_url)
        self.bedrock_client = None
        self.current_user: Optional[GitHubUser] = None
        
    def set_auth_token(self, auth_token: str, username: str = "user") -> GitHubUser:
        """Set authentication token for MCP server access"""
        self.mcp_client.update_token(auth_token)
        self.current_user = GitHubUser(username=username)
        logger.info(f"Set auth token for user: {username}")
        return self.current_user
        
    def _get_bedrock_client(self):
        """Get or create Bedrock client"""
        if not self.bedrock_client:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        return self.bedrock_client
        
    async def _create_system_prompt(self) -> str:
        """Create system prompt with available tools"""
        tools = await self.mcp_client.discover_tools()
        
        if not tools:
            return """You are a helpful assistant. However, no tools are currently available."""
            
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in tools
        ])
        
        return f"""You are a helpful assistant with access to the following tools:

{tools_description}

You can call these tools to help users with their requests. When you need to use a tool, respond with a JSON object containing:
- "tool_call": true
- "tool_name": the name of the tool to call
- "arguments": the arguments to pass to the tool

When you have the information needed to answer the user's question, respond normally without tool calls.

Available tools and their schemas:
{json.dumps(tools, indent=2)}
"""
    
    async def handle_request(self, prompt: str, auth_token: str = None) -> str:
        """Main entry point for handling user requests"""
        
        # Set auth token if provided
        if auth_token:
            self.set_auth_token(auth_token)
            
        if not self.mcp_client.auth_token:
            return "Please provide authentication token to access the MCP server."
        
        # Create system prompt with available tools
        system_prompt = await self._create_system_prompt()
        
        # Start conversation loop with LLM
        return await self._conversation_loop(system_prompt, prompt)
    
    async def _conversation_loop(self, system_prompt: str, user_prompt: str, max_iterations: int = 5) -> str:
        """Handle conversation with tool calling"""
        bedrock = self._get_bedrock_client()
        
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        for iteration in range(max_iterations):
            # Call LLM
            try:
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
                        tool_result = await self.mcp_client.call_tool(tool_name, arguments)
                        
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

# Lambda handler for AWS AgentCore
async def lambda_handler(event, context):
    """AWS Lambda handler for GitHub Development Assistant"""
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    # Create agent instance
    agent = GenericMCPAgent("https://api.githubcopilot.com/mcp/")
    
    # Extract payload
    payload = event.get("payload", {})
    user_message = payload.get("prompt", "Hello, what can you help me with?")
    
    # Get GitHub token from Authorization header or environment
    github_token = None
    if hasattr(context, 'request') and context.request and hasattr(context.request, 'headers'):
        auth_header = context.request.headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            github_token = auth_header[7:].strip()
    
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        logger.error("No GitHub token provided. Set GITHUB_TOKEN environment variable or pass Authorization: Bearer header.")
    
    # Process the request
    response = await agent.handle_request(user_message, github_token)
    
    return {"result": response}

# Test function for local development
async def test_agent():
    """Test the agent locally"""
    agent = GenericMCPAgent("https://api.githubcopilot.com/mcp/")
    
    # Mock context with test data
    test_payload = {
        "username": "testuser",
        "email": "test@example.com", 
        "name": "Test User",
        "groups": ["team-platform"],
        "github_token": os.getenv("GITHUB_TOKEN")
    }
    
    test_queries = [
        "What tools are available?",
        "List my recent pull requests",
        "Show me issues assigned to me",
        "Search for Python repositories"
    ]
    
    print("=== GitHub Development Assistant Test ===")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            response = await agent.handle_request(query, test_payload.get("github_token"))
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())