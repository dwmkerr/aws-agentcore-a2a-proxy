from strands import Agent, tool
from strands_tools import calculator, current_time
from strands.models import BedrockModel

# Import the AgentCore SDK
from bedrock_agentcore.runtime import BedrockAgentCoreApp

SYSTEM_PROMPT = """
You are a helpful customer support assistant.
When provided with a customer email, gather all necessary info and prepare the response email.
When asked about an order, look for it and tell the full description and date of the order to the customer.
Don't mention the customer ID in your reply.
"""

@tool
def get_customer_id(email_address: str):
    """Look up customer ID from email address"""
    if email_address == "me@example.net":
        return {"customer_id": 123}
    elif email_address == "test@example.com":
        return {"customer_id": 456}
    else:
        return {"message": "customer not found"}

@tool
def get_orders(customer_id: int):
    """Get customer orders by ID"""
    if customer_id == 123:
        return [{
            "order_id": 1234,
            "items": ["smartphone", "smartphone USB-C charger", "smartphone black cover"],
            "date": "2024-06-07"
        }]
    elif customer_id == 456:
        return [{
            "order_id": 5678,
            "items": ["laptop", "laptop charger", "wireless mouse"],
            "date": "2024-07-15"
        }]
    else:
        return {"message": "no order found"}

@tool
def get_knowledge_base_info(topic: str):
    """Get product information from knowledge base"""
    kb_info = []
    if "smartphone" in topic:
        if "cover" in topic:
            kb_info.append("To put on the cover, insert the bottom first, then push from the back up to the top.")
            kb_info.append("To remove the cover, push the top and bottom of the cover at the same time.")
        if "charger" in topic:
            kb_info.append("Input: 100-240V AC, 50/60Hz")
            kb_info.append("Includes US/UK/EU plug adapters")
    if "laptop" in topic:
        if "charger" in topic:
            kb_info.append("Compatible with 100-240V worldwide")
            kb_info.append("65W USB-C charger included")
    if len(kb_info) > 0:
        return kb_info
    else:
        return {"message": "no info found"}

# Create an AgentCore app
app = BedrockAgentCoreApp()

# Use Bedrock for both local and production  
model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0"  # Cheapest Claude model
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
)

# Specify the entry point function invoking the agent
@app.entrypoint
def invoke(payload):
    """Handler for agent invocation"""
    user_message = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()