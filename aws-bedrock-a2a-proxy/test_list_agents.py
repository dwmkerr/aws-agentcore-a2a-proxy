#!/usr/bin/env python3
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Create client with explicit credentials
client = boto3.client(
    'bedrock-agentcore-control',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

print("Testing list agents...")
try:
    response = client.list_agent_runtimes(maxResults=10)
    agents = response.get('agentRuntimes', [])
    print(f"✅ Success! Found {len(agents)} agents")
    for agent in agents:
        agent_id = agent.get('agentRuntimeId')
        print(f"  - Agent ID: {agent_id}")
except Exception as e:
    print(f"❌ Error: {e}")