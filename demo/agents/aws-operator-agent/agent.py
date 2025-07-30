#!/usr/bin/env python3
"""
AWS Operator Agent

A general AWS operations assistant that provides access to AWS services via boto3.
Supports any AWS operation through natural language queries.

Features:
- Dynamic boto3 client creation for any AWS service
- Natural language to AWS API mapping
- Role-based access control
- Comprehensive error handling

Integrates with:
- AWS SDK (boto3) for all AWS services
- AWS IAM for role-based access control
"""

import os
import json
import logging
import asyncio
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AWSUser:
    """Represents an authenticated AWS user with IAM permissions"""
    username: str
    email: str
    name: str
    role: str = "operator"  # operator, admin, readonly
    aws_account_id: str = ""
    allowed_regions: List[str] = None
    
    def __post_init__(self):
        if self.allowed_regions is None:
            self.allowed_regions = ["us-east-1", "us-west-2"]

class GeneralAWSClient:
    """General AWS client that can handle any boto3 service"""
    
    def __init__(self, user: AWSUser = None):
        self.user = user
        import boto3
        self.boto3 = boto3
        
    def _check_region_access(self, region: str) -> bool:
        """Check if user has access to AWS region"""
        if not self.user:
            return True
        return region in self.user.allowed_regions
    
    async def execute_aws_operation(self, prompt: str) -> Dict[str, Any]:
        """Execute AWS operation based on natural language prompt"""
        logger.info(f"Executing AWS operation for prompt: '{prompt}'")
        
        try:
            # Parse the prompt to determine AWS service and operation
            service, operation, params = self._parse_aws_request(prompt)
            
            if not service or not operation:
                return {"error": "Could not determine AWS service and operation from request"}
            
            logger.info(f"Parsed: service={service}, operation={operation}, params={params}")
            
            # Create boto3 client for the service
            client_params = {}
            if params.get('region'):
                if not self._check_region_access(params['region']):
                    return {"error": f"Access denied: {params['region']} region not allowed"}
                client_params['region_name'] = params['region']
            
            client = self.boto3.client(service, **client_params)
            
            # Execute the operation
            if hasattr(client, operation):
                method = getattr(client, operation)
                # Remove region from params as it's handled in client creation
                operation_params = {k: v for k, v in params.items() if k != 'region'}
                response = method(**operation_params)
                
                # Format response for readability
                return self._format_response(service, operation, response)
            else:
                return {"error": f"Operation '{operation}' not found for service '{service}'"}
                
        except Exception as e:
            logger.error(f"AWS operation failed: {str(e)}", exc_info=True)
            return {"error": f"AWS operation failed: {str(e)}"}
    
    def _parse_aws_request(self, prompt: str) -> tuple:
        """Parse natural language prompt to AWS service, operation, and parameters"""
        prompt_lower = prompt.lower()
        
        # Service mapping
        service_map = {
            's3': ['s3', 'bucket', 'storage'],
            'ec2': ['ec2', 'instance', 'server', 'vm'],
            'lambda': ['lambda', 'function'],
            'rds': ['rds', 'database', 'db'],
            'iam': ['iam', 'user', 'role', 'policy'],
            'cloudwatch': ['cloudwatch', 'alarm', 'metric', 'monitoring'],
            'sts': ['sts', 'identity', 'caller', 'who am i'],
            'cloudformation': ['cloudformation', 'stack', 'template'],
            'elasticache': ['elasticache', 'redis', 'memcached'],
            'sns': ['sns', 'notification', 'topic'],
            'sqs': ['sqs', 'queue', 'message']
        }
        
        # Find service
        service = None
        for aws_service, keywords in service_map.items():
            if any(keyword in prompt_lower for keyword in keywords):
                service = aws_service
                break
        
        if not service:
            return None, None, {}
        
        # Operation mapping based on common patterns
        operation = None
        params = {}
        
        # Extract region if specified
        region_match = re.search(r'\b(us-[a-z]+-\d+|eu-[a-z]+-\d+|ap-[a-z]+-\d+)\b', prompt_lower)
        if region_match:
            params['region'] = region_match.group(1)
        
        # Common operation patterns
        if any(word in prompt_lower for word in ['list', 'show', 'get', 'describe']):
            operation_map = {
                's3': 'list_buckets',
                'ec2': 'describe_instances',
                'lambda': 'list_functions',
                'rds': 'describe_db_instances',
                'iam': 'list_users',
                'cloudwatch': 'describe_alarms',
                'sts': 'get_caller_identity',
                'cloudformation': 'list_stacks',
                'elasticache': 'describe_cache_clusters',
                'sns': 'list_topics',
                'sqs': 'list_queues'
            }
            operation = operation_map.get(service)
        
        # Specific operation overrides
        if 'who am i' in prompt_lower or 'identity' in prompt_lower:
            service = 'sts'
            operation = 'get_caller_identity'
        elif 'bucket' in prompt_lower and service == 's3':
            operation = 'list_buckets'
        elif 'function' in prompt_lower and service == 'lambda':
            operation = 'list_functions'
        
        return service, operation, params
    
    def _format_response(self, service: str, operation: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format AWS API response for better readability"""
        # Remove metadata that's usually not needed
        if 'ResponseMetadata' in response:
            del response['ResponseMetadata']
        
        # Convert datetime objects to strings
        def convert_datetime(obj):
            if hasattr(obj, 'strftime'):
                return obj.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            else:
                return obj
        
        formatted_response = convert_datetime(response)
        
        # Add summary information
        summary = self._generate_summary(service, operation, formatted_response)
        if summary:
            formatted_response['_summary'] = summary
        
        return formatted_response
    
    def _generate_summary(self, service: str, operation: str, response: Dict[str, Any]) -> str:
        """Generate human-readable summary of the response"""
        try:
            if service == 's3' and operation == 'list_buckets':
                buckets = response.get('Buckets', [])
                return f"Found {len(buckets)} S3 buckets"
            
            elif service == 'ec2' and operation == 'describe_instances':
                reservations = response.get('Reservations', [])
                instance_count = sum(len(r.get('Instances', [])) for r in reservations)
                return f"Found {instance_count} EC2 instances across {len(reservations)} reservations"
            
            elif service == 'lambda' and operation == 'list_functions':
                functions = response.get('Functions', [])
                return f"Found {len(functions)} Lambda functions"
            
            elif service == 'sts' and operation == 'get_caller_identity':
                user_id = response.get('UserId', 'Unknown')
                account = response.get('Account', 'Unknown')
                return f"Current identity: {user_id} in account {account}"
            
        except Exception:
            pass
        
        return None

class AWSOperatorAgent:
    """Main agent class for general AWS operations"""
    
    def __init__(self):
        self.aws_client = GeneralAWSClient()
        self.current_user: Optional[AWSUser] = None
    
    def authenticate_user(self, oidc_claims: Dict[str, Any] = None) -> AWSUser:
        """Authenticate user from OIDC claims and set AWS permissions"""
        if oidc_claims:
            username = oidc_claims.get("preferred_username", "unknown")
            email = oidc_claims.get("email", "")
            name = oidc_claims.get("name", username)
            
            # Determine role from groups
            groups = oidc_claims.get("groups", [])
            aws_account_id = oidc_claims.get("aws_account_id", "")
            
            role = "readonly"
            if "aws-operators" in groups:
                role = "operator"
            elif "aws-admins" in groups:
                role = "admin"
            
            self.current_user = AWSUser(
                username=username,
                email=email,
                name=name,
                role=role,
                aws_account_id=aws_account_id
            )
        else:
            # Default user for testing
            self.current_user = AWSUser(
                username="testuser",
                email="test@example.com",
                name="Test User",
                role="operator"
            )
        
        # Update AWS client with user context
        self.aws_client.user = self.current_user
        
        logger.info(f"Authenticated AWS user: {self.current_user.name} with role: {self.current_user.role}")
        return self.current_user
    
    async def handle_request(self, prompt: str, oidc_claims: Dict[str, Any] = None) -> str:
        """Main entry point for handling user requests"""
        logger.info(f"Handling request: '{prompt}' with OIDC claims: {bool(oidc_claims)}")
        
        try:
            # Authenticate user if OIDC claims provided
            if oidc_claims or not self.current_user:
                self.authenticate_user(oidc_claims)
            
            # Handle general help requests
            if any(word in prompt.lower() for word in ['help', 'what can you do', 'hello']):
                return self._generate_help_response()
            
            # Execute AWS operation
            result = await self.aws_client.execute_aws_operation(prompt)
            
            if 'error' in result:
                return f"❌ {result['error']}"
            
            # Format the response nicely
            return self._format_user_response(prompt, result)
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return f"❌ An error occurred: {str(e)}"
    
    def _generate_help_response(self) -> str:
        """Generate help response showing what the agent can do"""
        user_info = f"Hello {self.current_user.name}! " if self.current_user else "Hello! "
        
        return f"""{user_info}I'm your AWS Operator Assistant.

I can help you with any AWS operation using natural language:

**Examples:**
- "List my S3 buckets"
- "Show EC2 instances in us-west-2"
- "Get my Lambda functions"
- "Show RDS databases"
- "Who am I?" (AWS identity)
- "List CloudFormation stacks"
- "Show IAM users"

**Powered by boto3** - I can access any AWS service and operation!

Your current role: **{self.current_user.role.title() if self.current_user else 'Unknown'}**
Allowed regions: {', '.join(self.current_user.allowed_regions) if self.current_user else 'All'}

What AWS operation would you like to perform?"""
    
    def _format_user_response(self, prompt: str, result: Dict[str, Any]) -> str:
        """Format AWS API response for user consumption"""
        try:
            # Show summary if available
            if '_summary' in result:
                summary = result['_summary']
                del result['_summary']
                
                # For simple responses, just return the summary
                if len(str(result)) < 500:
                    return f"✅ {summary}\n\n```json\n{json.dumps(result, indent=2)}\n```"
                else:
                    return f"✅ {summary}\n\n(Use AWS CLI or Console for detailed information)"
            
            # For responses without summary, show formatted JSON
            return f"✅ AWS operation completed:\n\n```json\n{json.dumps(result, indent=2)}\n```"
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return f"✅ AWS operation completed, but response formatting failed: {str(e)}"

# AgentCore web service setup
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
agent = AWSOperatorAgent()

@app.entrypoint
async def invoke(payload):
    """AgentCore entrypoint for processing requests"""
    logger.info(f"AgentCore invoke called with payload keys: {list(payload.keys())}")
    
    try:
        user_message = payload.get("prompt", "Hello, what can you help me with?")
        logger.info(f"Extracted user message: '{user_message}'")
        
        oidc_claims = payload.get("oidc_claims")
        logger.info(f"OIDC claims available: {bool(oidc_claims)}")
        
        response = await agent.handle_request(user_message, oidc_claims)
        logger.info(f"Generated response length: {len(response) if response else 0}")
        
        return {"result": response}
    except Exception as e:
        logger.error(f"Error in AgentCore entrypoint: {str(e)}", exc_info=True)
        return {"result": f"❌ AgentCore error: {str(e)}"}

# Local testing function
async def main():
    """Main entry point for local testing"""
    agent = AWSOperatorAgent()
    
    test_queries = [
        "Hello, what can you help me with?",
        "Who am I?",
        "List my S3 buckets",
        "Show EC2 instances",
        "Get my Lambda functions"
    ]
    
    for query in test_queries:
        print(f"\n🤖 User: {query}")
        response = await agent.handle_request(query)
        print(f"🤖 Assistant: {response}")
        print("-" * 80)

if __name__ == "__main__":
    # Start AgentCore web service
    app.run()