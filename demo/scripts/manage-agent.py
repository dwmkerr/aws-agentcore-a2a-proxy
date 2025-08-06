#!/usr/bin/env python3
"""
AWS Bedrock AgentCore management script using boto3 client.
Supports deploy and delete operations for agent runtimes.
"""

import boto3
import argparse
import time
import sys

# ANSI color constants
BLUE = "\033[34m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

# Simple logging functions
def log_info(msg):
    print(f"{BLUE}info{RESET}: {msg}")

def log_warning(msg):
    print(f"{YELLOW}warning{RESET}: {msg}")

def log_error(msg):
    print(f"{RED}error{RESET}: {msg}")


def main():
    parser = argparse.ArgumentParser(description='Manage AWS Bedrock AgentCore agents')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy an agent runtime')
    deploy_parser.add_argument('--agent-name', required=True, help='Name of the agent')
    deploy_parser.add_argument('--execution-role-arn', required=True, help='IAM execution role ARN')
    deploy_parser.add_argument('--image-uri', required=True, help='Container image URI')
    deploy_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    deploy_parser.add_argument('--description', help='Agent description (optional)')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an agent runtime')
    delete_parser.add_argument('--agent-name', required=True, help='Name of the agent to delete')
    delete_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'deploy':
        deploy_agent(args)
    elif args.command == 'delete':
        delete_agent(args)


def create_client(region):
    """Create boto3 client for AgentCore Control Plane"""
    try:
        cp_endpoint_url = f"https://bedrock-agentcore-control.{region}.amazonaws.com"
        client = boto3.client(
            'bedrock-agentcore-control',
            region_name=region,
            endpoint_url=cp_endpoint_url
        )
        log_info(f"connected to bedrock-agentcore-control in {region}")
        return client
    except Exception as e:
        log_error(f"failed to create boto3 client: {e}")
        sys.exit(1)


def wait_for_agent_status(client, agent_id, target_status='READY', max_attempts=30):
    """Wait for agent to reach target status"""
    for attempt in range(max_attempts):
        try:
            response = client.get_agent_runtime(agentRuntimeId=agent_id)
            current_status = response.get('status', 'UNKNOWN')
            
            log_info(f"status: {current_status} (attempt {attempt + 1}/{max_attempts})")
            
            if current_status == target_status:
                return True
            elif current_status in ['FAILED', 'DELETED', 'UPDATE_FAILED']:
                log_error(f"agent failed with status: {current_status}")
                return False
                
            time.sleep(30)
            
        except Exception as e:
            log_warning(f"could not check status: {e}")
            time.sleep(30)
    
    log_warning(f"timeout waiting for status {target_status}")
    return False


def find_agent_by_name(client, agent_name):
    """Find existing agent by name"""
    try:
        response = client.list_agent_runtimes(maxResults=100)
        
        for agent in response.get('agentRuntimes', []):
            runtime_name = agent.get('agentRuntimeName')
            runtime_id = agent.get('agentRuntimeId', '')
            
            if (runtime_name == agent_name or 
                (runtime_id.startswith(agent_name + '-') if runtime_id else False)):
                return agent
        
        return None
    except Exception as e:
        log_error(f"failed to list agents: {e}")
        return None


def create_agent_runtime(client, agent_name, image_uri, role_arn, description=None):
    """Create new agent runtime"""
    agent_description = description or f"{agent_name.replace('_', ' ').replace('-', ' ').title()} agent"
    
    try:
        response = client.create_agent_runtime(
            agentRuntimeName=agent_name,
            description=agent_description,
            agentRuntimeArtifact={
                'containerConfiguration': {
                    'containerUri': image_uri
                }
            },
            networkConfiguration={
                'networkMode': 'PUBLIC'
            },
            roleArn=role_arn
        )
        
        return {
            'agent_id': response.get('agentRuntimeId'),
            'agent_arn': response.get('agentRuntimeArn'),
            'status': response.get('status', 'CREATING')
        }
        
    except Exception as e:
        log_error(f"failed to create agent: {e}")
        return None


def update_agent_runtime(client, agent_id, image_uri, role_arn, description=None):
    """Update existing agent runtime"""
    update_params = {
        'agentRuntimeId': agent_id,
        'agentRuntimeArtifact': {
            'containerConfiguration': {
                'containerUri': image_uri
            }
        },
        'networkConfiguration': {
            'networkMode': 'PUBLIC'
        },
        'roleArn': role_arn
    }
    
    if description:
        update_params['description'] = description
    
    try:
        response = client.update_agent_runtime(**update_params)
        
        return {
            'agent_id': response.get('agentRuntimeId'),
            'agent_arn': response.get('agentRuntimeArn'),
            'version': response.get('agentRuntimeVersion'),
            'status': response.get('status', 'UPDATING')
        }
        
    except Exception as e:
        log_error(f"failed to update agent: {e}")
        return None


def deploy_agent(args):
    """Deploy an agent runtime"""
    agent_name = args.agent_name
    execution_role_arn = args.execution_role_arn
    image_uri = args.image_uri
    region = args.region
    description = args.description
    
    client = create_client(region)
    
    # Check if agent already exists
    existing_agent = find_agent_by_name(client, agent_name)
    
    if existing_agent:
        agent_id = existing_agent.get('agentRuntimeId')
        log_info(f"agent '{agent_name}' already exists (id: {agent_id}), updating with new image")
        
        # Update existing agent
        update_result = update_agent_runtime(client, agent_id, image_uri, execution_role_arn, description)
        
        if not update_result:
            log_error("failed to update agent runtime")
            sys.exit(1)
        
        new_version = update_result.get('version', 'unknown')
        log_info(f"created new version {new_version}")
        
        # Wait for update to complete
        if wait_for_agent_status(client, agent_id, 'READY', max_attempts=20):
            log_info(f"agent {agent_name} updated to version {new_version} and ready")
        else:
            log_warning("agent update may still be in progress")
    
    else:
        log_info(f"creating new agent {agent_name}")
        
        # Create new agent
        result = create_agent_runtime(client, agent_name, image_uri, execution_role_arn, description)
        
        if not result:
            log_error("failed to create agent runtime")
            sys.exit(1)
        
        agent_id = result['agent_id']
        log_info(f"created agent with id: {agent_id}")
        
        # Wait for deployment
        if wait_for_agent_status(client, agent_id, 'READY', max_attempts=30):
            log_info(f"agent {agent_name} is ready")
        else:
            log_warning("agent deployment may still be in progress")
    
    log_info(f"Agent '{agent_name}' deployment completed")


def delete_agent(args):
    """Delete an agent runtime"""
    agent_name = args.agent_name
    region = args.region
    
    client = create_client(region)
    
    log_info(f"deleting AgentCore runtime '{agent_name}'")
    
    # Find agent to delete
    log_info("finding agent to delete...")
    agent = find_agent_by_name(client, agent_name)
    
    if not agent:
        log_error(f"agent '{agent_name}' not found!")
        print()
        list_all_agents(client)
        sys.exit(1)
    
    agent_id = agent.get('agentRuntimeId')
    agent_status = agent.get('status', 'Unknown')
    log_info(f"found agent: {agent_id} (status: {agent_status})")
    
    # Check if agent is already being deleted
    if agent_status == 'DELETING':
        log_warning(f"agent '{agent_name}' is already being deleted")
        return
    
    # Delete agent
    log_info("deleting agent runtime...")
    try:
        client.delete_agent_runtime(agentRuntimeId=agent_id)
        log_info("agent runtime deleted successfully")
        log_info(f"agent '{agent_name}' has been deleted")
        log_info("you can now run deployment again to create a new agent")
    except Exception as e:
        log_error(f"failed to delete agent '{agent_name}': {e}")
        sys.exit(1)


def list_all_agents(client):
    """List all available agents for user reference"""
    try:
        response = client.list_agent_runtimes(maxResults=100)
        agents = response.get('agentRuntimes', [])
        
        if agents:
            print("Available agents:")
            for agent in agents:
                runtime_id = agent.get('agentRuntimeId', 'Unknown')
                agent_name = agent.get('agentRuntimeName', 'None')
                status = agent.get('status', 'Unknown')
                print(f"  - Name: {agent_name}, ID: {runtime_id}, Status: {status}")
        else:
            print("No agents found")
            
    except Exception as e:
        log_error(f"failed to list agents: {e}")


if __name__ == "__main__":
    main()