#!/usr/bin/env python3
"""
Shared AWS AgentCore client and request signing utilities.
"""

import json
import os
import hashlib
import hmac
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse


class AWSRequest:
    """AWS API request signer using SigV4"""
    
    def __init__(self, access_key, secret_key, region, service):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
    
    def _sign_key(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    def _get_signature_key(self, date_stamp):
        k_date = self._sign_key(('AWS4' + self.secret_key).encode('utf-8'), date_stamp)
        k_region = self._sign_key(k_date, self.region)
        k_service = self._sign_key(k_region, self.service)
        k_signing = self._sign_key(k_service, 'aws4_request')
        return k_signing
    
    def sign_request(self, method, url, headers=None, payload=''):
        """Sign AWS API request with SigV4"""
        if headers is None:
            headers = {}
        
        # Parse URL
        parsed = urlparse(url)
        host = parsed.netloc
        canonical_uri = parsed.path or '/'
        canonical_querystring = parsed.query or ''
        
        # Create timestamp
        t = datetime.now(timezone.utc)
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')
        
        # Add required headers
        headers['Host'] = host
        headers['X-Amz-Date'] = amzdate
        
        # Create canonical headers
        signed_headers = ';'.join(sorted([k.lower() for k in headers.keys()]))
        canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())]) + '\n'
        
        # Create payload hash
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # Create canonical request
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{datestamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Calculate signature
        signing_key = self._get_signature_key(datestamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Add authorization header
        authorization_header = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        headers['Authorization'] = authorization_header
        
        return headers


class AgentCoreWebClient:
    """Direct web API client for AWS AgentCore operations"""
    
    def __init__(self, region='us-east-1'):
        """
        Initialize AgentCore web client.
        
        Required environment variables:
        - AWS_ACCESS_KEY_ID: Your AWS access key
        - AWS_SECRET_ACCESS_KEY: Your AWS secret key  
        - AWS_REGION: AWS region (optional, defaults to us-east-1)
        
        These should be set in ../../.env file for the Makefile to work.
        """
        self.region = region
        self.access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        if not self.access_key or not self.secret_key:
            raise ValueError(
                "AWS credentials not found in environment variables.\n"
                "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.\n" 
                "For Makefile usage, add them to ../../.env file."
            )
        
        self.signer = AWSRequest(self.access_key, self.secret_key, region, 'bedrock-agentcore')
        self.base_url = f"https://bedrock-agentcore-control.{region}.amazonaws.com"
    
    def list_agent_runtimes(self, max_results=100):
        """List all agent runtimes"""
        url = f"{self.base_url}/runtimes/?maxResults={max_results}"
        headers = {'Content-Type': 'application/json'}
        payload = '{}'
        
        signed_headers = self.signer.sign_request('POST', url, headers, payload)
        
        try:
            response = requests.post(url, headers=signed_headers, data=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get('agentRuntimes', [])
            else:
                print(f"❌ Failed to list agents: {response.status_code}")
                print(f"Response: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
            return []
    
    def create_agent_runtime(self, agent_name, image_uri, execution_role_arn):
        """Create AgentCore agent runtime"""
        url = f"{self.base_url}/runtimes/"
        
        payload = {
            "agentRuntimeName": agent_name,
            "description": f"{agent_name.replace('_', ' ').title()} deployed via web API - IAM auth",
            "agentRuntimeArtifact": {
                "containerConfiguration": {
                    "containerUri": image_uri
                }
            },
            "roleArn": execution_role_arn,
            "networkConfiguration": {
                "networkMode": "PUBLIC"
            },
            "protocolConfiguration": {
                "serverProtocol": "HTTP"
            },
            # Explicitly configure for IAM authentication (not OAuth)
            "authorizerConfiguration": {
                "type": "IAM"  # Explicit IAM auth instead of default OAuth
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        signed_headers = self.signer.sign_request('PUT', url, headers, json.dumps(payload))
        
        try:
            response = requests.put(url, headers=signed_headers, data=json.dumps(payload), timeout=60)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'agent_id': result.get('agentRuntimeId'),
                    'agent_arn': result.get('agentRuntimeArn'),
                    'status': result.get('status', 'CREATING')
                }
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error calling API: {e}")
            return None
    
    def delete_agent_runtime(self, agent_id):
        """Delete AgentCore agent runtime by ID"""
        url = f"{self.base_url}/runtimes/{agent_id}/"
        headers = {'Content-Type': 'application/json'}
        
        signed_headers = self.signer.sign_request('DELETE', url, headers, '')
        
        try:
            response = requests.delete(url, headers=signed_headers, timeout=60)
            return response.status_code in [200, 202, 204]
        except Exception as e:
            print(f"❌ Error calling API: {e}")
            return False
    
    def get_agent_status(self, agent_id):
        """Get agent runtime status"""
        url = f"{self.base_url}/runtimes/{agent_id}"
        headers = {'Content-Type': 'application/json'}
        
        signed_headers = self.signer.sign_request('GET', url, headers, '')
        
        try:
            response = requests.get(url, headers=signed_headers, timeout=30)
            if response.status_code == 200:
                return response.json().get('agentRuntime', {})
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return None
    
    def find_agent_by_name(self, agent_name):
        """Find agent by name or name pattern"""
        agents = self.list_agent_runtimes()
        
        for agent in agents:
            runtime_id = agent.get('agentRuntimeId', '')
            agent_name_field = agent.get('agentRuntimeName')
            
            # Match by name OR by runtime ID pattern (starts with agent_name)
            if (agent_name_field == agent_name or 
                (runtime_id.startswith(agent_name + '-') if runtime_id else False)):
                return agent
        
        return None
    
    def invoke_agent_runtime(self, agent_id, payload):
        """Invoke AgentCore agent runtime via direct web API (not A2A)"""
        # This would be the direct AgentCore invocation for Bedrock
        # Currently requires bearer tokens (OAuth/Cognito), not IAM
        # NOTE: AgentCore doesn't have full SDK support yet in preview
        
        url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/agents/{agent_id}/invoke"
        headers = {'Content-Type': 'application/json'}
        
        # This would need bearer token authentication for OAuth-configured agents
        # For now, we'll try with IAM signing but expect it to fail with current agent config
        signed_headers = self.signer.sign_request('POST', url, headers, json.dumps(payload))
        
        try:
            response = requests.post(url, headers=signed_headers, data=json.dumps(payload), timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Agent invocation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error invoking agent: {e}")
            return None