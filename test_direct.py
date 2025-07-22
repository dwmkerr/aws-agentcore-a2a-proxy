#!/usr/bin/env python3
import boto3
import json
import uuid
import urllib.parse
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest as BotocoreAWSRequest
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials using default credential chain (like working example)
session = boto3.Session()
credentials = session.get_credentials()

# Agent details
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:705383350627:runtime/Bedrock_Customer_Support_Agent-IjyJ7O5PgN"
session_id = str(uuid.uuid4())

# Create request URL
escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
url = f'https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{escaped_agent_arn}/invocations'

# Create request
request = BotocoreAWSRequest(
    method='POST', 
    url=url,
    data=json.dumps({'prompt': 'Hello, I need help with my order'}),
    headers={
        'Content-Type': 'application/json',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id
    }
)

print(f"Testing direct HTTPS call...")
print(f"URL: {url}")
print(f"Access key: {credentials.access_key[:8]}...")
print(f"Session ID: {session_id}")

# Sign the request
SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)

# Make the request
response = requests.post(request.url, headers=dict(request.headers), data=request.data, timeout=60)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Success! Response: {response.json()}")
else:
    print(f"Error: {response.text}")