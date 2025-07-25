#!/usr/bin/env python3
"""
Delete AgentCore agent using shared AWS client.
"""

import sys
from aws_agentcore_client import AgentCoreWebClient


def main():
    if len(sys.argv) != 2:
        print("Usage: python undeploy-via-api.py <agent_name>")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    
    print(f"🗑️  Deleting AgentCore runtime via web API...")
    print(f"📋 Agent Name: {agent_name}")
    
    # Create client
    client = AgentCoreWebClient()
    
    # Find agent
    print("🔍 Finding agent to delete...")
    agent = client.find_agent_by_name(agent_name)
    
    if not agent:
        print(f"❌ Agent '{agent_name}' not found!")
        print(f"Available agents:")
        
        agents = client.list_agent_runtimes()
        for agent in agents:
            runtime_id = agent.get('agentRuntimeId', 'Unknown')
            agent_name_field = agent.get('agentRuntimeName', 'None')
            status = agent.get('status', 'Unknown')
            print(f"  - Name: {agent_name_field}, ID: {runtime_id}, Status: {status}")
        
        sys.exit(1)
    
    agent_id = agent.get('agentRuntimeId')
    print(f"🎯 Found agent: {agent_id}")
    
    # Delete agent
    if client.delete_agent_runtime(agent_id):
        print(f"✅ Agent runtime deleted successfully!")
        print(f"🎯 Agent '{agent_name}' has been deleted!")
        print(f"💡 You can now run 'make deploy' to create a new agent")
    else:
        print(f"❌ Failed to delete agent '{agent_name}'")
        sys.exit(1)


if __name__ == "__main__":
    main()