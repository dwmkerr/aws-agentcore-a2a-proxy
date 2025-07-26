import json
import logging
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class AgentCoreClient:
    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.use_default_credentials = not access_key_id or not secret_access_key

        try:
            # Only create control client for listing agents
            # Runtime invocation will use direct HTTPS calls since boto3 bedrock-agentcore doesn't exist
            if self.use_default_credentials:
                self.control_client = boto3.client("bedrock-agentcore-control", region_name=region)
            else:
                self.control_client = boto3.client(
                    "bedrock-agentcore-control",
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    region_name=region,
                )

            logger.info(f"Initialized AgentCore client for region {region} (using direct HTTPS for invocation)")

        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
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

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"AWS ClientError listing agents: {error_code} - {error_message}")

            if error_code == "AccessDeniedException":
                logger.error("Access denied. Check IAM permissions for bedrock-agentcore:ListAgentRuntimes")
            elif error_code == "UnauthorizedOperation":
                logger.error("Unauthorized operation. Verify AWS credentials and permissions")

            raise

        except BotoCoreError as e:
            logger.error(f"BotoCoreError listing agents: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error listing agents: {e}")
            raise

    async def invoke_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Invoking agent {agent_id} via direct HTTPS (access_key: {self.access_key_id[:8]}...)")

            agent_arn = self._get_agent_arn(agent_id)

            # Extract text from payload
            if isinstance(payload, dict) and "prompt" in payload:
                input_text = payload["prompt"]
            else:
                input_text = str(payload)

            # Generate session ID for this invocation
            import uuid

            session_id = str(uuid.uuid4())

            logger.info(f"Agent ARN: {agent_arn}")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Prompt: {input_text}")

            # Use direct HTTPS request since boto3 bedrock-agentcore client doesn't exist
            import urllib.parse
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest as BotocoreAWSRequest
            import requests

            # Create direct HTTPS request
            base_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            escaped_agent_arn = urllib.parse.quote(agent_arn, safe="")
            url = f"{base_url}/runtimes/{escaped_agent_arn}/invocations"

            request_payload = json.dumps({"prompt": input_text})

            # Create AWS request using botocore for proper signing
            request = BotocoreAWSRequest(
                method="POST",
                url=url,
                data=request_payload,
                headers={"Content-Type": "application/json", "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id},
            )

            # Sign with botocore's SigV4Auth using default credential chain (like working example)
            import boto3

            session = boto3.Session()  # Use default credential chain
            credentials = session.get_credentials()
            logger.info(f"Signing with credentials: {credentials.access_key[:8]}...")
            SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)

            # Make the request
            if not request.url:
                raise ValueError("Request URL is None")
            response = requests.post(request.url, headers=dict(request.headers), data=request.data, timeout=60)

            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info("Agent response received successfully")
                return result
            else:
                error_text = response.text
                logger.error(f"Agent invocation failed: {response.status_code} - {error_text}")
                raise Exception(f"Agent invocation failed: {response.status_code} - {error_text}")

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
