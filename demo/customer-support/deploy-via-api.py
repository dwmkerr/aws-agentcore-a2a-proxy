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
    
    print(f"🚀 Creating AgentCore runtime via web API...")
    print(f"📋 Agent: {agent_name}")
    print(f"📋 Image: {image_uri}")
    print(f"🔐 Role: {execution_role_arn}")
    
    # Create client and deploy
    client = AgentCoreWebClient()
    
    result = client.create_agent_runtime(agent_name, image_uri, execution_role_arn)
    
    if result:
        agent_id = result['agent_id']
        
        print(f"✅ Agent runtime created successfully!")
        print(f"🆔 Agent ID: {agent_id}")
        print(f"🔗 Agent ARN: {result['agent_arn']}")
        
        # Wait for deployment
        print(f"⏳ Waiting for agent {agent_id} to be ready...")
        
        for i in range(30):  # Wait up to 15 minutes
            time.sleep(30)
            status_info = client.get_agent_status(agent_id)
            
            if status_info:
                status = status_info.get('status', 'UNKNOWN')
                print(f"🔄 Status: {status}")
                
                if status == 'READY':
                    print(f"✅ Agent {agent_id} is ready!")
                    print(f"🌐 A2A Address: localhost:2972/a2a/agent/{agent_id}")
                    break
                elif status in ['FAILED', 'DELETED']:
                    print(f"❌ Agent deployment failed with status: {status}")
                    sys.exit(1)
            else:
                print("⚠️ Could not check status")
        
        print(f"\n🎯 Next steps:")
        print(f"1. Call POST http://localhost:2972/rpc/initialize to discover this agent")
        print(f"2. Use A2A endpoint: localhost:2972/a2a/agent/{agent_id}")
        
    else:
        print("❌ Failed to create agent runtime")
        sys.exit(1)


if __name__ == "__main__":
    main()