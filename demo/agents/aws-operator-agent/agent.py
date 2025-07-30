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

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

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

# Global user context - will be set by authentication
current_user: Optional[AWSUser] = None

def _check_region_access(region: str) -> bool:
    """Check if current user has access to specified AWS region"""
    if not current_user:
        return True  # Allow all regions if no user context
    return region in current_user.allowed_regions

def _handle_aws_error(e: Exception, operation: str) -> Dict[str, Any]:
    """Handle AWS exceptions and return structured error response"""
    if isinstance(e, ClientError):
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS ClientError in {operation}: {error_code} - {error_message}")
        return {
            "error": f"AWS {operation} failed: {error_code} - {error_message}",
            "error_code": error_code
        }
    elif isinstance(e, BotoCoreError):
        logger.error(f"BotoCoreError in {operation}: {str(e)}")
        return {"error": f"AWS connection error in {operation}: {str(e)}"}
    else:
        logger.error(f"Unexpected error in {operation}: {str(e)}")
        return {"error": f"Unexpected error in {operation}: {str(e)}"}

# S3 Tools
@tool
def list_s3_buckets(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all S3 buckets in your AWS account.
    
    Args:
        region: AWS region to connect from (default: us-east-1)
        
    Returns:
        Dictionary containing list of buckets with names and creation dates
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('s3', region_name=region)
        response = client.list_buckets()
        
        buckets = response.get('Buckets', [])
        # Convert datetime objects to strings
        for bucket in buckets:
            if 'CreationDate' in bucket:
                bucket['CreationDate'] = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S UTC')
        
        return {
            "buckets": buckets,
            "bucket_count": len(buckets),
            "summary": f"Found {len(buckets)} S3 buckets"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_s3_buckets")

@tool
def get_s3_bucket_info(bucket_name: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Get detailed information about a specific S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket to inspect
        region: AWS region to connect from (default: us-east-1)
        
    Returns:
        Dictionary containing bucket location, versioning status, and object count
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('s3', region_name=region)
        
        # Get bucket location
        try:
            location = client.get_bucket_location(Bucket=bucket_name)
            bucket_region = location.get('LocationConstraint') or 'us-east-1'
        except ClientError:
            bucket_region = "unknown"
        
        # Get versioning status
        try:
            versioning = client.get_bucket_versioning(Bucket=bucket_name)
            versioning_status = versioning.get('Status', 'Disabled')
        except ClientError:
            versioning_status = "unknown"
        
        # Count objects (first 1000)
        try:
            objects = client.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)
            object_count = objects.get('KeyCount', 0)
            is_truncated = objects.get('IsTruncated', False)
            count_note = f"~{object_count}+" if is_truncated else str(object_count)
        except ClientError:
            count_note = "unknown"
        
        return {
            "bucket_name": bucket_name,
            "region": bucket_region,
            "versioning_status": versioning_status,
            "object_count": count_note,
            "summary": f"Bucket {bucket_name} in {bucket_region} with {count_note} objects"
        }
    except Exception as e:
        return _handle_aws_error(e, "get_s3_bucket_info")

# EC2 Tools
@tool
def list_ec2_instances(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all EC2 instances in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing instance details including ID, type, state, and tags
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('ec2', region_name=region)
        response = client.describe_instances()
        
        instances = []
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                # Extract key information
                instance_info = {
                    "instance_id": instance.get('InstanceId'),
                    "instance_type": instance.get('InstanceType'),
                    "state": instance.get('State', {}).get('Name'),
                    "private_ip": instance.get('PrivateIpAddress'),
                    "public_ip": instance.get('PublicIpAddress'),
                    "launch_time": instance.get('LaunchTime').strftime('%Y-%m-%d %H:%M:%S UTC') if instance.get('LaunchTime') else None,
                    "tags": {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                }
                instances.append(instance_info)
        
        return {
            "instances": instances,
            "instance_count": len(instances),
            "region": region,
            "summary": f"Found {len(instances)} EC2 instances in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_ec2_instances")

@tool
def get_ec2_instance_details(instance_id: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Get detailed information about a specific EC2 instance.
    
    Args:
        instance_id: The EC2 instance ID (e.g., i-1234567890abcdef0)
        region: AWS region where the instance is located (default: us-east-1)
        
    Returns:
        Dictionary containing comprehensive instance details
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('ec2', region_name=region)
        response = client.describe_instances(InstanceIds=[instance_id])
        
        if not response.get('Reservations'):
            return {"error": f"Instance {instance_id} not found in {region}"}
        
        instance = response['Reservations'][0]['Instances'][0]
        
        return {
            "instance_id": instance.get('InstanceId'),
            "instance_type": instance.get('InstanceType'),
            "state": instance.get('State', {}).get('Name'),
            "private_ip": instance.get('PrivateIpAddress'),
            "public_ip": instance.get('PublicIpAddress'),
            "launch_time": instance.get('LaunchTime').strftime('%Y-%m-%d %H:%M:%S UTC') if instance.get('LaunchTime') else None,
            "availability_zone": instance.get('Placement', {}).get('AvailabilityZone'),
            "security_groups": [sg.get('GroupName') for sg in instance.get('SecurityGroups', [])],
            "tags": {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])},
            "vpc_id": instance.get('VpcId'),
            "subnet_id": instance.get('SubnetId'),
            "summary": f"Instance {instance_id} is {instance.get('State', {}).get('Name')} in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "get_ec2_instance_details")

# Lambda Tools
@tool
def list_lambda_functions(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all Lambda functions in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing function names, runtimes, and last modified dates
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('lambda', region_name=region)
        response = client.list_functions()
        
        functions = []
        for func in response.get('Functions', []):
            function_info = {
                "function_name": func.get('FunctionName'),
                "runtime": func.get('Runtime'),
                "handler": func.get('Handler'),
                "memory_size": func.get('MemorySize'),
                "timeout": func.get('Timeout'),
                "last_modified": func.get('LastModified'),
                "code_size": func.get('CodeSize'),
                "description": func.get('Description', '')
            }
            functions.append(function_info)
        
        return {
            "functions": functions,
            "function_count": len(functions),
            "region": region,
            "summary": f"Found {len(functions)} Lambda functions in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_lambda_functions")

@tool
def get_lambda_function_details(function_name: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Get detailed configuration for a specific Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        region: AWS region where the function is located (default: us-east-1)
        
    Returns:
        Dictionary containing function configuration, environment variables, and VPC settings
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('lambda', region_name=region)
        response = client.get_function(FunctionName=function_name)
        
        config = response.get('Configuration', {})
        
        return {
            "function_name": config.get('FunctionName'),
            "function_arn": config.get('FunctionArn'),
            "runtime": config.get('Runtime'),
            "handler": config.get('Handler'),
            "memory_size": config.get('MemorySize'),
            "timeout": config.get('Timeout'),
            "last_modified": config.get('LastModified'),
            "code_size": config.get('CodeSize'),
            "description": config.get('Description', ''),
            "environment_variables": config.get('Environment', {}).get('Variables', {}),
            "vpc_config": config.get('VpcConfig', {}),
            "role": config.get('Role'),
            "summary": f"Function {function_name} using {config.get('Runtime')} with {config.get('MemorySize')}MB memory"
        }
    except Exception as e:
        return _handle_aws_error(e, "get_lambda_function_details")

# RDS Tools
@tool
def list_rds_instances(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all RDS database instances in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing database instance details including engine, status, and size
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('rds', region_name=region)
        response = client.describe_db_instances()
        
        instances = []
        for db in response.get('DBInstances', []):
            instance_info = {
                "db_instance_identifier": db.get('DBInstanceIdentifier'),
                "db_instance_class": db.get('DBInstanceClass'),
                "engine": db.get('Engine'),
                "engine_version": db.get('EngineVersion'),
                "db_instance_status": db.get('DBInstanceStatus'),
                "allocated_storage": db.get('AllocatedStorage'),
                "storage_type": db.get('StorageType'),
                "multi_az": db.get('MultiAZ'),
                "availability_zone": db.get('AvailabilityZone'),
                "publicly_accessible": db.get('PubliclyAccessible'),
                "creation_time": db.get('InstanceCreateTime').strftime('%Y-%m-%d %H:%M:%S UTC') if db.get('InstanceCreateTime') else None
            }
            instances.append(instance_info)
        
        return {
            "db_instances": instances,
            "instance_count": len(instances),
            "region": region,
            "summary": f"Found {len(instances)} RDS instances in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_rds_instances")

# IAM Tools
@tool
def list_iam_users() -> Dict[str, Any]:
    """
    List all IAM users in the AWS account.
    
    Returns:
        Dictionary containing user details including usernames, creation dates, and paths
    """
    try:
        client = boto3.client('iam')
        response = client.list_users()
        
        users = []
        for user in response.get('Users', []):
            user_info = {
                "username": user.get('UserName'),
                "user_id": user.get('UserId'),
                "path": user.get('Path'),
                "create_date": user.get('CreateDate').strftime('%Y-%m-%d %H:%M:%S UTC') if user.get('CreateDate') else None,
                "password_last_used": user.get('PasswordLastUsed').strftime('%Y-%m-%d %H:%M:%S UTC') if user.get('PasswordLastUsed') else None
            }
            users.append(user_info)
        
        return {
            "users": users,
            "user_count": len(users),
            "summary": f"Found {len(users)} IAM users"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_iam_users")

@tool
def get_caller_identity() -> Dict[str, Any]:
    """
    Get the current AWS caller identity (who am I?).
    
    Returns:
        Dictionary containing current user/role ARN, account ID, and user ID
    """
    try:
        client = boto3.client('sts')
        response = client.get_caller_identity()
        
        return {
            "user_id": response.get('UserId'),
            "account": response.get('Account'),
            "arn": response.get('Arn'),
            "summary": f"Current identity: {response.get('UserId')} in account {response.get('Account')}"
        }
    except Exception as e:
        return _handle_aws_error(e, "get_caller_identity")

# CloudFormation Tools
@tool
def list_cloudformation_stacks(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all CloudFormation stacks in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing stack names, statuses, and creation times
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('cloudformation', region_name=region)
        response = client.list_stacks()
        
        # Filter out deleted stacks
        active_stacks = [
            stack for stack in response.get('StackSummaries', [])
            if stack.get('StackStatus') != 'DELETE_COMPLETE'
        ]
        
        stacks = []
        for stack in active_stacks:
            stack_info = {
                "stack_name": stack.get('StackName'),
                "stack_status": stack.get('StackStatus'),
                "creation_time": stack.get('CreationTime').strftime('%Y-%m-%d %H:%M:%S UTC') if stack.get('CreationTime') else None,
                "last_updated_time": stack.get('LastUpdatedTime').strftime('%Y-%m-%d %H:%M:%S UTC') if stack.get('LastUpdatedTime') else None,
                "template_description": stack.get('TemplateDescription', '')
            }
            stacks.append(stack_info)
        
        return {
            "stacks": stacks,
            "stack_count": len(stacks),
            "region": region,
            "summary": f"Found {len(stacks)} active CloudFormation stacks in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_cloudformation_stacks")

# SNS Tools
@tool
def list_sns_topics(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all SNS topics in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing topic ARNs and names
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('sns', region_name=region)
        response = client.list_topics()
        
        topics = []
        for topic in response.get('Topics', []):
            topic_arn = topic.get('TopicArn')
            topic_name = topic_arn.split(':')[-1] if topic_arn else 'unknown'
            topics.append({
                "topic_arn": topic_arn,
                "topic_name": topic_name
            })
        
        return {
            "topics": topics,
            "topic_count": len(topics),
            "region": region,
            "summary": f"Found {len(topics)} SNS topics in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_sns_topics")

# SQS Tools
@tool
def list_sqs_queues(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all SQS queues in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        Dictionary containing queue URLs and names
    """
    try:
        if not _check_region_access(region):
            return {"error": f"Access denied: {region} region not allowed"}
            
        client = boto3.client('sqs', region_name=region)
        response = client.list_queues()
        
        queue_urls = response.get('QueueUrls', [])
        queues = []
        
        for queue_url in queue_urls:
            queue_name = queue_url.split('/')[-1] if queue_url else 'unknown'
            queues.append({
                "queue_url": queue_url,
                "queue_name": queue_name
            })
        
        return {
            "queues": queues,
            "queue_count": len(queues),
            "region": region,
            "summary": f"Found {len(queues)} SQS queues in {region}"
        }
    except Exception as e:
        return _handle_aws_error(e, "list_sqs_queues")

# Create the system prompt
SYSTEM_PROMPT = f"""
You are an AWS Operator Assistant with access to comprehensive AWS tools.

**Your Role:**
- Provide secure, efficient AWS operations using structured tools
- Follow role-based access controls and region restrictions  
- Give clear, actionable responses with proper error handling

**Available AWS Services:**
- **S3**: List buckets, get bucket details
- **EC2**: List instances, get instance details  
- **Lambda**: List functions, get function configuration
- **RDS**: List database instances
- **IAM**: List users, get caller identity
- **CloudFormation**: List stacks
- **SNS**: List topics
- **SQS**: List queues

**Current User Context:**
- Role: {current_user.role.title() if current_user else 'Unknown'}
- Allowed Regions: {', '.join(current_user.allowed_regions) if current_user else 'All'}

**Guidelines:**
- Always use the appropriate tool for each AWS operation
- Include region parameter when relevant (default: us-east-1)
- Provide summaries with key insights from tool results
- Handle errors gracefully and suggest alternatives when possible
- Respect user's regional access restrictions

Example queries you can handle:
- "List my S3 buckets"
- "Show EC2 instances in us-west-2" 
- "Get details for instance i-1234567890abcdef0"
- "What Lambda functions do I have?"
- "Who am I?" (AWS identity)
- "List my CloudFormation stacks"
"""

# Create the agent with all tools
app = BedrockAgentCoreApp()

model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)

# Define all available tools
aws_tools = [
    # S3 tools
    list_s3_buckets,
    get_s3_bucket_info,
    # EC2 tools  
    list_ec2_instances,
    get_ec2_instance_details,
    # Lambda tools
    list_lambda_functions,
    get_lambda_function_details,
    # RDS tools
    list_rds_instances,
    # IAM tools
    list_iam_users,
    get_caller_identity,
    # CloudFormation tools
    list_cloudformation_stacks,
    # SNS tools
    list_sns_topics,
    # SQS tools
    list_sqs_queues
]

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=aws_tools
)

def authenticate_user(oidc_claims: Dict[str, Any] = None) -> AWSUser:
    """Authenticate user from OIDC claims and set AWS permissions"""
    global current_user
    
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
        
        current_user = AWSUser(
            username=username,
            email=email,
            name=name,
            role=role,
            aws_account_id=aws_account_id
        )
    else:
        # Default user for testing
        current_user = AWSUser(
            username="testuser",
            email="test@example.com",
            name="Test User",
            role="operator"
        )
    
    logger.info(f"Authenticated AWS user: {current_user.name} with role: {current_user.role}")
    return current_user

@app.entrypoint
def invoke(payload):
    """AgentCore entrypoint for processing requests"""
    logger.info(f"AgentCore invoke called with payload keys: {list(payload.keys())}")
    
    try:
        user_message = payload.get("prompt", "Hello! What AWS operation would you like to perform?")
        logger.info(f"Extracted user message: '{user_message}'")
        
        # Authenticate user if OIDC claims provided
        oidc_claims = payload.get("oidc_claims")
        if oidc_claims or not current_user:
            authenticate_user(oidc_claims)
        
        # Update system prompt with current user context
        updated_system_prompt = SYSTEM_PROMPT.format(
            role=current_user.role.title() if current_user else 'Unknown',
            regions=', '.join(current_user.allowed_regions) if current_user else 'All'
        )
        agent.system_prompt = updated_system_prompt
        
        result = agent(user_message)
        logger.info(f"Generated response length: {len(result.message) if result.message else 0}")
        
        return {"result": result.message}
    except Exception as e:
        logger.error(f"Error in AgentCore entrypoint: {str(e)}", exc_info=True)
        return {"result": f"❌ AgentCore error: {str(e)}"}

if __name__ == "__main__":
    # For local testing
    app.run()