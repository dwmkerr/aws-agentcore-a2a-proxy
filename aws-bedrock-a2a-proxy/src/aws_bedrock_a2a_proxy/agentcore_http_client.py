"""HTTP client for AWS Bedrock AgentCore API"""

import json
import logging
import urllib.parse
from typing import Dict, Any, List, AsyncIterator, Optional

import boto3
import requests
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest as BotocoreAWSRequest

logger = logging.getLogger(__name__)


class AgentCoreHTTPClient:
    """HTTP client for AWS Bedrock AgentCore API communication"""

    def __init__(
        self, region: str = "us-east-1", access_key_id: Optional[str] = None, secret_access_key: Optional[str] = None
    ):
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self._session: Optional[boto3.Session] = None

    def _get_session(self) -> boto3.Session:
        """Get or create boto3 session"""
        if self._session is None:
            if self.access_key_id and self.secret_access_key:
                self._session = boto3.Session(
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region,
                )
            else:
                self._session = boto3.Session(region_name=self.region)
        return self._session

    def _create_signed_request(
        self, method: str, url: str, data: Optional[str] = None, headers: Optional[Dict[str, str]] = None
    ) -> BotocoreAWSRequest:
        """Create a signed AWS request"""
        headers = headers or {}
        request = BotocoreAWSRequest(method=method, url=url, data=data, headers=headers)

        session = self._get_session()
        credentials = session.get_credentials()
        SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)

        return request

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all AgentCore agents"""
        try:
            base_url = f"https://bedrock-agentcore-control.{self.region}.amazonaws.com"
            url = f"{base_url}/agent-runtimes"

            request = self._create_signed_request("GET", url)

            logger.info(f"Listing AgentCore agents from {url}")
            if not request.url:
                raise ValueError("Request URL is None")
            response = requests.get(request.url, headers=dict(request.headers), timeout=30)

            logger.info(f"List agents response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                agents = result.get("agentRuntimes", [])
                logger.info(f"Found {len(agents)} agents")
                return agents
            else:
                error_text = response.text
                logger.error(f"Failed to list agents: {response.status_code} - {error_text}")
                raise Exception(f"Failed to list agents: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise

    async def invoke_agent(self, agent_id: str, prompt: str) -> Dict[str, Any]:
        """Invoke an AgentCore agent with a prompt"""
        try:
            # Get agent ARN from stored agents or construct it
            agent_arn = self._get_agent_arn(agent_id)

            # Generate session ID for this invocation
            import uuid

            session_id = str(uuid.uuid4())

            logger.info(f"Invoking agent {agent_id} with prompt: {prompt[:100]}...")
            logger.info(f"Agent ARN: {agent_arn}")
            logger.info(f"Session ID: {session_id}")

            # Create direct HTTPS request
            base_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            escaped_agent_arn = urllib.parse.quote(agent_arn, safe="")
            url = f"{base_url}/runtimes/{escaped_agent_arn}/invocations"

            request_payload = json.dumps({"prompt": prompt})
            headers = {"Content-Type": "application/json", "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id}

            request = self._create_signed_request("POST", url, request_payload, headers)

            # Make the request
            if not request.url:
                raise ValueError("Request URL is None")
            response = requests.post(request.url, headers=dict(request.headers), data=request.data, timeout=60)

            logger.info(f"Agent invocation response status: {response.status_code}")

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

    async def invoke_agent_stream(self, agent_id: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """Invoke an AgentCore agent with streaming response"""
        try:
            # Get agent ARN from stored agents or construct it
            agent_arn = self._get_agent_arn(agent_id)

            # Generate session ID for this invocation
            import uuid

            session_id = str(uuid.uuid4())

            logger.info(f"Streaming invoke agent {agent_id} with prompt: {prompt[:100]}...")
            logger.info(f"Agent ARN: {agent_arn}")
            logger.info(f"Session ID: {session_id}")

            # Create direct HTTPS request for streaming
            base_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            escaped_agent_arn = urllib.parse.quote(agent_arn, safe="")
            url = f"{base_url}/runtimes/{escaped_agent_arn}/invocations"

            request_payload = json.dumps({"prompt": prompt})
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",  # Use standard JSON for now
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
                "X-Amzn-Bedrock-AgentCore-Enable-Streaming": "true",  # Request streaming
            }

            # Create signed request for streaming
            request = self._create_signed_request("POST", url, request_payload, headers)

            # Use httpx for async streaming
            if not request.url:
                raise ValueError("Request URL is None")
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST", request.url, headers=dict(request.headers), content=request.data
                ) as response:

                    logger.info(f"Streaming response status: {response.status_code}")
                    logger.info(f"Response headers: {dict(response.headers)}")

                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Streaming invocation failed: {response.status_code} - {error_text}")
                        raise Exception(f"Streaming invocation failed: {response.status_code} - {error_text}")

                    # First, let's see what we get in the response
                    content_type = response.headers.get("content-type", "")
                    logger.info(f"Response Content-Type: {content_type}")

                    # Process Server-Sent Events or streaming JSON
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        logger.info(f"Line {line_count}: {line[:200]}...")

                        if line.strip():
                            try:
                                # Try to parse as JSON chunk
                                if line.startswith("data: "):
                                    line = line[6:]  # Remove 'data: ' prefix
                                if line == "[DONE]":
                                    break

                                chunk_data = json.loads(line)
                                logger.info(f"Received streaming chunk: {str(chunk_data)[:100]}...")
                                yield chunk_data

                            except json.JSONDecodeError:
                                # Handle non-JSON streaming data
                                logger.info(f"Received non-JSON chunk: {line[:100]}...")
                                yield {"text": line.strip()}

                    if line_count == 0:
                        logger.warning("No lines received from streaming response")

        except Exception as e:
            logger.error(f"Error in streaming invocation for agent {agent_id}: {e}")
            raise

    def _get_agent_arn(self, agent_id: str) -> str:
        """Get agent ARN from agent ID"""
        # Construct ARN using known format
        # Format: arn:aws:bedrock-agentcore:region:account:runtime/agent-id
        return f"arn:aws:bedrock-agentcore:{self.region}:705383350627:runtime/{agent_id}"
