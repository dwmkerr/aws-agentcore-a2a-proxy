import json
import logging
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AgentCoreClient:
    def __init__(self, region: str = "us-east-1"):
        self.region = region

        try:
            # Use AWS credential chain - boto3 handles env vars, IAM roles, etc.
            self.control_client = boto3.client("bedrock-agentcore-control", region_name=region)
            logger.info(f"Initialized AgentCore client for region {region} using AWS credential chain")

        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            logger.error(
                "Ensure AWS credentials are configured via credential chain "
                "(env vars, IAM roles, ~/.aws/credentials, etc.)"
            )
            raise

    async def list_agents(self) -> List[Dict[str, Any]]:
        try:
            logger.info("Listing AgentCore agents...")

            response = self.control_client.list_agent_runtimes(maxResults=100)
            agents = response.get("agentRuntimes", [])

            logger.info(f"Found {len(agents)} agent runtimes")

            for agent in agents:
                logger.info(
                    f"Agent: {agent.get('agentRuntimeId')} - {agent.get('agentRuntimeName')} - "
                    f"Status: {agent.get('status')}"
                )

            return agents

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise

    async def invoke_agent(self, agent_id: str, payload: Dict[str, Any], streaming: bool = False) -> Dict[str, Any]:
        """Invoke AgentCore agent using official AWS SDK, handles both streaming and non-streaming"""
        try:
            agent_arn = self._get_agent_arn(agent_id)

            # Extract text from payload
            if isinstance(payload, dict) and "prompt" in payload:
                prompt = payload["prompt"]
            else:
                prompt = str(payload)

            # Generate session ID for this invocation
            import uuid

            session_id = str(uuid.uuid4())

            logger.info(f"Invoking agent {agent_id} (streaming: {streaming}) with prompt: {prompt[:100]}...")
            logger.info(f"Agent ARN: {agent_arn}")
            logger.info(f"Session ID: {session_id}")

            # Use official AWS SDK with credential chain
            client = boto3.client("bedrock-agentcore", region_name=self.region)

            # Prepare the payload
            request_payload = json.dumps({"prompt": prompt}).encode()

            # Use asyncio to run the synchronous boto3 call in a thread pool
            import asyncio

            def sync_invoke():
                return client.invoke_agent_runtime(
                    agentRuntimeArn=agent_arn, runtimeSessionId=session_id, payload=request_payload
                )

            # Run the sync call in executor
            response = await asyncio.get_event_loop().run_in_executor(None, sync_invoke)

            logger.info(f"Response content type: {response.get('contentType', 'unknown')}")

            # Handle streaming vs non-streaming response based on content type
            if "text/event-stream" in response.get("contentType", ""):
                # Handle streaming response - return the response object for the caller to process
                logger.info("Received streaming response from AWS")
                return {
                    "streaming": True,
                    "content_type": response.get("contentType"),
                    "response": response["response"],  # Iterator for streaming chunks
                }

            elif response.get("contentType") == "application/json":
                # Handle standard JSON response
                logger.info("Received JSON response from AWS")
                content = []
                for chunk in response.get("response", []):
                    content.append(chunk.decode("utf-8"))

                if content:
                    try:
                        json_response = json.loads("".join(content))
                        logger.debug(f"Parsed JSON response: {str(json_response)[:100]}...")
                        return {"streaming": False, "content_type": "application/json", "result": json_response}
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        return {
                            "streaming": False,
                            "content_type": "application/json",
                            "error": "Failed to parse JSON response",
                            "raw": "".join(content),
                        }
                else:
                    # Handle empty content
                    logger.warning("Received empty JSON response from AWS")
                    return {
                        "streaming": False,
                        "content_type": "application/json",
                        "error": "Empty response",
                        "result": None,
                    }

            else:
                # Handle other content types
                logger.warning(f"Unexpected content type: {response.get('contentType')}")
                return {
                    "streaming": False,
                    "content_type": response.get("contentType"),
                    "error": "Unexpected content type",
                    "response": str(response),
                }

        except Exception as e:
            logger.error(f"Error invoking agent {agent_id}: {e}")
            raise

    def _get_agent_arn(self, agent_id: str) -> str:
        # Use the actual runtime ARN format from agent discovery
        return f"arn:aws:bedrock-agentcore:{self.region}:705383350627:runtime/{agent_id}"

    async def get_agent_details(self, agent_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.control_client.describe_agent_runtime(agentRuntimeId=agent_id)
            return response.get("agentRuntime")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise

        except Exception as e:
            logger.error(f"Error getting agent details for {agent_id}: {e}")
            return None
