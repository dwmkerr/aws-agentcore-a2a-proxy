#!/usr/bin/env python3
"""
Deploy AgentCore agent using shared AWS client.
"""

import sys
import time
from aws_agentcore_client import AgentCoreWebClient


def main():
    if len(sys.argv) != 4:
        print("Usage: python deploy-via-api.py <agent_name> <image_uri> <execution_role_arn>")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    image_uri = sys.argv[2]
    execution_role_arn = sys.argv[3]
    
    # Create client
    client = AgentCoreWebClient()
    
    # Check if agent already exists and remove it
    existing_agent = client.find_agent_by_name(agent_name)
    if existing_agent:
        agent_id = existing_agent.get('agentRuntimeId')
        print(f"\033[1;37minfo:\033[0m agent '{agent_name}' already exists (id: {agent_id}), removing first")
        
        if client.delete_agent_runtime(agent_id):
            print(f"\033[1;37minfo:\033[0m existing agent removed successfully")
            # Wait a moment for cleanup
            time.sleep(5)
        else:
            print(f"\033[1;31merror:\033[0m failed to remove existing agent")
            sys.exit(1)
    
    print(f"\033[1;37minfo:\033[0m creating agent {agent_name}")
    
    result = client.create_agent_runtime(agent_name, image_uri, execution_role_arn)
    
    if result:
        agent_id = result['agent_id']
        
        # Wait for deployment
        for i in range(30):  # Wait up to 15 minutes
            time.sleep(30)
            status_info = client.get_agent_status(agent_id)
            
            if status_info:
                status = status_info.get('status', 'UNKNOWN')
                
                if status == 'READY':
                    print(f"\033[1;37minfo:\033[0m agent {agent_name} is ready")
                    break
                elif status in ['FAILED', 'DELETED']:
                    print(f"\033[1;31merror:\033[0m agent deployment failed with status: {status.lower()}")
                    sys.exit(1)
            else:
                print("could not check status")
        
    else:
        print(f"\033[1;31merror:\033[0m failed to create agent runtime")
        sys.exit(1)


if __name__ == "__main__":
    main()