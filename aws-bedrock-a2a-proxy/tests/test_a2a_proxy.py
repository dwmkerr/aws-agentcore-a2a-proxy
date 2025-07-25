"""Tests for A2AProxy and AgentCoreExecutor"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid
from fastapi import HTTPException

from aws_bedrock_a2a_proxy.a2a_proxy import A2AProxy, AgentCoreExecutor
from aws_bedrock_a2a_proxy.agentcore_client import AgentCoreClient
from aws_bedrock_a2a_proxy.agentcore_http_client import AgentCoreHTTPClient


@pytest.fixture
def mock_agentcore_client():
    """Mock AgentCoreClient"""
    client = Mock(spec=AgentCoreClient)
    client.invoke_agent = AsyncMock()
    return client


@pytest.fixture
def a2a_proxy(mock_agentcore_client):
    """Create A2AProxy instance"""
    return A2AProxy(mock_agentcore_client)


@pytest.fixture
def sample_agents():
    """Sample agent data"""
    return [
        {
            "agentRuntimeId": "agent-1",
            "agentRuntimeName": "Test Agent 1",
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-1",
            "description": "Test agent 1 description",
            "status": "READY",
            "agentRuntimeVersion": "1",
            "lastUpdatedAt": "2023-01-01T00:00:00Z"
        },
        {
            "agentRuntimeId": "agent-2", 
            "agentRuntimeName": "Test Agent 2",
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-2",
            "description": "Test agent 2 description",
            "status": "READY",
            "agentRuntimeVersion": "2",
            "lastUpdatedAt": "2023-01-02T00:00:00Z"
        }
    ]


class TestA2AProxy:
    """Test cases for A2AProxy"""
    
    def test_init(self, mock_agentcore_client):
        """Test A2AProxy initialization"""
        proxy = A2AProxy(mock_agentcore_client)
        
        assert proxy.client == mock_agentcore_client
        assert proxy.agents == {}
        assert proxy.a2a_apps == {}
        assert proxy.a2a_router is not None
    
    def test_get_router(self, a2a_proxy):
        """Test get_router method"""
        router = a2a_proxy.get_router()
        assert router == a2a_proxy.a2a_router
    
    @pytest.mark.asyncio
    async def test_initialize_agents(self, a2a_proxy, sample_agents):
        """Test agent initialization"""
        with patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCard'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreHTTPClient'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreExecutor'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.DefaultRequestHandler'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.A2AStarletteApplication'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.InMemoryTaskStore'):
            
            await a2a_proxy.initialize_agents(sample_agents)
        
        # Verify agents were stored
        assert len(a2a_proxy.agents) == 2
        assert "agent-1" in a2a_proxy.agents
        assert "agent-2" in a2a_proxy.agents
        assert a2a_proxy.agents["agent-1"]["agentRuntimeName"] == "Test Agent 1"
        assert a2a_proxy.agents["agent-2"]["agentRuntimeName"] == "Test Agent 2"
    
    @pytest.mark.asyncio
    async def test_initialize_agents_with_missing_ids(self, a2a_proxy):
        """Test agent initialization with agents missing IDs"""
        agents_with_missing_id = [
            {"agentRuntimeName": "Agent Without ID"},
            {"agentRuntimeId": "agent-1", "agentRuntimeName": "Valid Agent"}
        ]
        
        with patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCard'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreHTTPClient'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreExecutor'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.DefaultRequestHandler'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.A2AStarletteApplication'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.InMemoryTaskStore'):
            
            await a2a_proxy.initialize_agents(agents_with_missing_id)
        
        # Only agent with ID should be stored
        assert len(a2a_proxy.agents) == 1
        assert "agent-1" in a2a_proxy.agents
    
    @pytest.mark.asyncio
    async def test_invoke_agent_success(self, a2a_proxy, mock_agentcore_client):
        """Test successful agent invocation"""
        # Setup agent
        a2a_proxy.agents["agent-1"] = {"agentRuntimeName": "Test Agent"}
        
        # Mock response
        expected_response = {"result": {"content": [{"text": "Agent response"}]}}
        mock_agentcore_client.invoke_agent.return_value = expected_response
        
        # Test invocation
        result = await a2a_proxy.invoke_agent("agent-1", {"prompt": "test"})
        
        assert result == expected_response
        mock_agentcore_client.invoke_agent.assert_called_once_with("agent-1", {"prompt": "test"})
    
    @pytest.mark.asyncio
    async def test_invoke_agent_not_found(self, a2a_proxy):
        """Test invoking non-existent agent"""
        with pytest.raises(ValueError, match="Agent non-existent not found"):
            await a2a_proxy.invoke_agent("non-existent", {"prompt": "test"})
    
    @pytest.mark.asyncio
    async def test_invoke_agent_client_error(self, a2a_proxy, mock_agentcore_client):
        """Test agent invocation with client error"""
        # Setup agent
        a2a_proxy.agents["agent-1"] = {"agentRuntimeName": "Test Agent"}
        
        # Mock client error
        mock_agentcore_client.invoke_agent.side_effect = Exception("Client error")
        
        # Test should re-raise the exception
        with pytest.raises(Exception, match="Client error"):
            await a2a_proxy.invoke_agent("agent-1", {"prompt": "test"})
    
    @pytest.mark.asyncio
    async def test_shutdown(self, a2a_proxy, sample_agents):
        """Test proxy shutdown"""
        # Initialize with some agents
        with patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCard'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreHTTPClient'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.AgentCoreExecutor'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.DefaultRequestHandler'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.A2AStarletteApplication'), \
             patch('aws_bedrock_a2a_proxy.a2a_proxy.InMemoryTaskStore'):
            
            await a2a_proxy.initialize_agents(sample_agents)
        
        # Verify agents are present
        assert len(a2a_proxy.agents) == 2
        
        # Shutdown
        await a2a_proxy.shutdown()
        
        # Verify cleanup
        assert len(a2a_proxy.agents) == 0
        assert len(a2a_proxy.a2a_apps) == 0
    
    def test_get_agent_addresses(self, a2a_proxy, sample_agents):
        """Test getting agent A2A addresses"""
        # Manually add agents (without full initialization)
        for agent in sample_agents:
            agent_id = agent.get('agentRuntimeId')
            if agent_id:
                a2a_proxy.agents[agent_id] = agent
        
        addresses = a2a_proxy.get_agent_addresses()
        
        assert len(addresses) == 2
        assert addresses[0]["agent_id"] == "agent-1"
        assert addresses[0]["agent_name"] == "Test Agent 1"
        assert addresses[0]["a2a_address"] == "localhost:2972/a2a/agent/agent-1"
        assert addresses[0]["status"] == "READY"
        
        assert addresses[1]["agent_id"] == "agent-2"
        assert addresses[1]["agent_name"] == "Test Agent 2"
        assert addresses[1]["a2a_address"] == "localhost:2972/a2a/agent/agent-2"
        assert addresses[1]["status"] == "READY"
    
    def test_get_agent_addresses_with_missing_name(self, a2a_proxy):
        """Test getting agent addresses when agent name is missing"""
        # Add agent without name
        a2a_proxy.agents["agent-1"] = {"status": "READY"}
        
        addresses = a2a_proxy.get_agent_addresses()
        
        assert len(addresses) == 1
        assert addresses[0]["agent_name"] == "agent-agent-1"  # fallback name
    
    def test_get_agent_addresses_empty(self, a2a_proxy):
        """Test getting agent addresses when no agents present"""
        addresses = a2a_proxy.get_agent_addresses()
        assert addresses == []


class TestA2AProxyEndpoints:
    """Test A2A proxy HTTP endpoints"""
    
    @pytest.fixture
    def initialized_proxy(self, a2a_proxy, sample_agents):
        """A2A proxy with initialized agents"""
        # Manually add agents to avoid complex mocking
        for agent in sample_agents:
            agent_id = agent.get('agentRuntimeId')
            if agent_id:
                a2a_proxy.agents[agent_id] = agent
        return a2a_proxy
    
    @pytest.mark.asyncio
    async def test_list_a2a_agents_endpoint(self, initialized_proxy):
        """Test /a2a/agents endpoint"""
        # Get the router and find the endpoint function
        router = initialized_proxy.get_router()
        
        # Manually call the endpoint function
        # Note: In a real test, you'd use FastAPI TestClient
        from fastapi import Request
        
        # Find the list_a2a_agents function from router
        list_agents_route = None
        for route in router.routes:
            if hasattr(route, 'path') and route.path == "/a2a/agents":
                list_agents_route = route
                break
        
        assert list_agents_route is not None
        
        # Test the endpoint function directly
        # The endpoint is an async function, so we call it directly
        endpoint_func = list_agents_route.endpoint
        result = await endpoint_func()
        
        assert len(result) == 2
        assert result[0]["agent_id"] == "agent-1"
        assert result[0]["name"] == "Test Agent 1"
        assert result[0]["host"] == "localhost:2972"
        assert result[0]["endpoint"] == "/a2a/agent/agent-1"
        assert result[0]["status"] == "READY"
        
        assert result[1]["agent_id"] == "agent-2"
        assert result[1]["name"] == "Test Agent 2"
    
    @pytest.mark.asyncio
    async def test_list_agentcore_agents_endpoint(self, initialized_proxy):
        """Test /agentcore/agents endpoint"""
        router = initialized_proxy.get_router()
        
        # Find the agentcore agents endpoint
        agentcore_route = None
        for route in router.routes:
            if hasattr(route, 'path') and route.path == "/agentcore/agents":
                agentcore_route = route
                break
        
        assert agentcore_route is not None
        
        # Test the endpoint function
        endpoint_func = agentcore_route.endpoint
        result = await endpoint_func()
        
        assert len(result) == 2
        assert result[0]["agentRuntimeId"] == "agent-1"
        assert result[0]["agentRuntimeName"] == "Test Agent 1"
        assert result[0]["agentRuntimeArn"] == "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-1"
        assert result[0]["status"] == "READY"
        
        assert result[1]["agentRuntimeId"] == "agent-2"
        assert result[1]["agentRuntimeName"] == "Test Agent 2"
    
    @pytest.mark.asyncio
    async def test_get_agent_card_endpoint(self, initialized_proxy):
        """Test /a2a/agent/{agent_id}/.well-known/agent.json endpoint"""
        router = initialized_proxy.get_router()
        
        # Find the agent card endpoint
        card_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/.well-known/agent.json" in route.path:
                card_route = route
                break
        
        assert card_route is not None
        
        # Test the endpoint function
        endpoint_func = card_route.endpoint
        result = await endpoint_func("agent-1")
        
        assert result["name"] == "Test Agent 1"
        assert result["description"] == "Test agent 1 description"
        assert result["capabilities"]["streaming"] is True
        assert result["capabilities"]["pushNotifications"] is False
        assert result["version"] == "1"
        assert result["metadata"]["runtime_id"] == "agent-1"
    
    @pytest.mark.asyncio
    async def test_get_agent_card_not_found(self, initialized_proxy):
        """Test agent card endpoint with non-existent agent"""
        router = initialized_proxy.get_router()
        
        # Find the agent card endpoint
        card_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/.well-known/agent.json" in route.path:
                card_route = route
                break
        
        endpoint_func = card_route.endpoint
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint_func("non-existent")
        
        assert exc_info.value.status_code == 404
        assert "Agent non-existent not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_invoke_agentcore_agent_endpoint(self, initialized_proxy, mock_agentcore_client):
        """Test /agentcore/agents/{agent_id}/invoke endpoint"""
        router = initialized_proxy.get_router()
        
        # Mock the client response
        mock_response = {"result": {"content": [{"text": "Agent response"}]}}
        mock_agentcore_client.invoke_agent.return_value = mock_response
        
        # Find the invoke endpoint
        invoke_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/agentcore/agents/" in route.path and "/invoke" in route.path:
                invoke_route = route
                break
        
        assert invoke_route is not None
        
        # Test the endpoint function
        endpoint_func = invoke_route.endpoint
        payload = {"prompt": "test message"}
        result = await endpoint_func("agent-1", payload)
        
        assert result == mock_response
        mock_agentcore_client.invoke_agent.assert_called_once_with("agent-1", payload)
    
    @pytest.mark.asyncio
    async def test_invoke_agentcore_agent_not_found(self, initialized_proxy):
        """Test invoke endpoint with non-existent agent"""
        router = initialized_proxy.get_router()
        
        # Find the invoke endpoint
        invoke_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/agentcore/agents/" in route.path and "/invoke" in route.path:
                invoke_route = route
                break
        
        endpoint_func = invoke_route.endpoint
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint_func("non-existent", {"prompt": "test"})
        
        assert exc_info.value.status_code == 404
        assert "Agent non-existent not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_invoke_agentcore_agent_client_error(self, initialized_proxy, mock_agentcore_client):
        """Test invoke endpoint with client error"""
        router = initialized_proxy.get_router()
        
        # Mock client error
        mock_agentcore_client.invoke_agent.side_effect = Exception("Client error")
        
        # Find the invoke endpoint
        invoke_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/agentcore/agents/" in route.path and "/invoke" in route.path:
                invoke_route = route
                break
        
        endpoint_func = invoke_route.endpoint
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint_func("agent-1", {"prompt": "test"})
        
        assert exc_info.value.status_code == 500
        assert "Client error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_jsonrpc_endpoint(self, initialized_proxy, mock_agentcore_client):
        """Test /a2a/agent/{agent_id}/jsonrpc endpoint"""
        # Add a2a apps for the agent
        initialized_proxy.a2a_apps["agent-1"] = Mock()
        
        router = initialized_proxy.get_router()
        
        # Mock the client response
        mock_response = {"result": {"content": [{"text": "Agent response"}]}}
        mock_agentcore_client.invoke_agent.return_value = mock_response
        
        # Find the jsonrpc endpoint
        jsonrpc_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/jsonrpc" in route.path:
                jsonrpc_route = route
                break
        
        assert jsonrpc_route is not None
        
        # Test the endpoint function
        endpoint_func = jsonrpc_route.endpoint
        request_data = {"method": "query", "params": {"query": "test"}, "id": 1}
        result = await endpoint_func("agent-1", request_data)
        
        assert result == {"result": "Agent response"}
        mock_agentcore_client.invoke_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_jsonrpc_endpoint_malformed_response(self, initialized_proxy, mock_agentcore_client):
        """Test JSON-RPC endpoint with malformed AgentCore response"""
        # Add a2a apps for the agent
        initialized_proxy.a2a_apps["agent-1"] = Mock()
        
        router = initialized_proxy.get_router()
        
        # Mock a malformed response that doesn't match expected format
        mock_response = {"unexpected": "format"}
        mock_agentcore_client.invoke_agent.return_value = mock_response
        
        # Find the jsonrpc endpoint
        jsonrpc_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/jsonrpc" in route.path:
                jsonrpc_route = route
                break
        
        assert jsonrpc_route is not None
        
        # Test the endpoint function
        endpoint_func = jsonrpc_route.endpoint
        request_data = {"method": "query", "params": {"query": "test"}, "id": 1}
        result = await endpoint_func("agent-1", request_data)
        
        # Should return the raw result when format doesn't match expected
        assert result == mock_response
        mock_agentcore_client.invoke_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_jsonrpc_endpoint_client_error(self, initialized_proxy, mock_agentcore_client):
        """Test JSON-RPC endpoint with client error"""
        # Add a2a apps for the agent
        initialized_proxy.a2a_apps["agent-1"] = Mock()
        
        router = initialized_proxy.get_router()
        
        # Mock client error
        mock_agentcore_client.invoke_agent.side_effect = Exception("Client error")
        
        # Find the jsonrpc endpoint
        jsonrpc_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/jsonrpc" in route.path:
                jsonrpc_route = route
                break
        
        endpoint_func = jsonrpc_route.endpoint
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint_func("agent-1", {"method": "query"})
        
        assert exc_info.value.status_code == 500
        assert "Client error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_jsonrpc_endpoint_not_found(self, initialized_proxy):
        """Test JSON-RPC endpoint with non-existent agent"""
        router = initialized_proxy.get_router()
        
        # Find the jsonrpc endpoint
        jsonrpc_route = None
        for route in router.routes:
            if hasattr(route, 'path') and "/jsonrpc" in route.path:
                jsonrpc_route = route
                break
        
        endpoint_func = jsonrpc_route.endpoint
        
        with pytest.raises(HTTPException) as exc_info:
            await endpoint_func("non-existent", {"method": "query"})
        
        assert exc_info.value.status_code == 404
        assert "Agent non-existent not found" in str(exc_info.value.detail)


class TestAgentCoreExecutor:
    """Test cases for AgentCoreExecutor class"""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock AgentCoreHTTPClient"""
        client = Mock(spec=AgentCoreHTTPClient)
        client.invoke_agent = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_context(self):
        """Mock A2A context"""
        context = Mock()
        context.task_id = "test-task-id"
        
        # Mock message with text parts
        message = Mock()
        message.contextId = "test-context-id"
        
        part = Mock()
        text_part = Mock()
        text_part.text = "Hello, test message"
        part.root = text_part
        
        message.parts = [part]
        context.message = message
        
        return context
    
    @pytest.fixture
    def mock_event_queue(self):
        """Mock A2A event queue"""
        queue = Mock()
        queue.enqueue_event = AsyncMock()
        return queue
    
    @pytest.fixture
    def executor(self, mock_http_client):
        """Create AgentCoreExecutor instance"""
        return AgentCoreExecutor(mock_http_client, "test-agent-id")
    
    def test_executor_init(self, mock_http_client):
        """Test executor initialization"""
        executor = AgentCoreExecutor(mock_http_client, "test-agent")
        
        assert executor.http_client == mock_http_client
        assert executor.agent_id == "test-agent"
    
    @pytest.mark.asyncio
    async def test_executor_execute_success(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test successful agent execution"""
        # Mock AgentCore response
        mock_http_client.invoke_agent.return_value = {
            "result": {
                "role": "assistant",
                "content": [{"text": "Agent response text"}]
            }
        }
        
        # Execute
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify HTTP client was called
        mock_http_client.invoke_agent.assert_called_once_with("test-agent-id", "Hello, test message")
        
        # Verify response was enqueued
        mock_event_queue.enqueue_event.assert_called_once()
        call_args = mock_event_queue.enqueue_event.call_args[0][0]
        
        # Check the response message
        assert call_args.taskId == "test-task-id"
        assert call_args.contextId == "test-context-id"
        assert len(call_args.parts) == 1
        assert call_args.parts[0].root.text == "Agent response text"
    
    @pytest.mark.asyncio
    async def test_executor_execute_no_message(self, executor, mock_http_client, mock_event_queue):
        """Test execution with no message"""
        context = Mock()
        context.task_id = "test-task-id"
        context.message = None
        
        mock_http_client.invoke_agent.return_value = {
            "result": {
                "role": "assistant",
                "content": [{"text": "Response"}]
            }
        }
        
        await executor.execute(context, mock_event_queue)
        
        # Should handle None message gracefully
        mock_http_client.invoke_agent.assert_called_once_with("test-agent-id", "")
    
    @pytest.mark.asyncio
    async def test_executor_execute_malformed_response(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test execution with malformed response"""
        # Mock malformed response
        mock_http_client.invoke_agent.return_value = {"unexpected": "format"}
        
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify fallback to string representation
        call_args = mock_event_queue.enqueue_event.call_args[0][0]
        assert "unexpected" in call_args.parts[0].root.text
    
    @pytest.mark.asyncio
    async def test_executor_execute_error(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test execution when HTTP client raises exception"""
        # Mock HTTP client error
        mock_http_client.invoke_agent.side_effect = Exception("HTTP request failed")
        
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify error response was enqueued
        mock_event_queue.enqueue_event.assert_called_once()
        call_args = mock_event_queue.enqueue_event.call_args[0][0]
        
        assert "Error: HTTP request failed" in call_args.parts[0].root.text
        assert call_args.taskId == "test-task-id"
    
    @pytest.mark.asyncio
    async def test_executor_cancel(self, executor, mock_context, mock_event_queue):
        """Test cancel method (no-op for AgentCore)"""
        # Cancel should not raise any exceptions
        await executor.cancel(mock_context, mock_event_queue)
        
        # No events should be enqueued for cancel
        mock_event_queue.enqueue_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_executor_complex_response(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test execution with complex response containing multiple text parts"""
        # Mock AgentCore response with multiple text parts
        mock_http_client.invoke_agent.return_value = {
            "result": {
                "role": "assistant",
                "content": [
                    {"text": "First part "},
                    {"text": "Second part "},
                    {"text": "Third part"}
                ]
            }
        }
        
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify concatenated response
        call_args = mock_event_queue.enqueue_event.call_args[0][0]
        assert call_args.parts[0].root.text == "First part Second part Third part"