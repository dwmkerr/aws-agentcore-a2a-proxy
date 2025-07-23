"""Tests for AgentCoreExecutor"""

import pytest
from unittest.mock import Mock, AsyncMock
import uuid

from aws_bedrock_a2a_proxy.a2a_proxy import AgentCoreExecutor
from aws_bedrock_a2a_proxy.agentcore_http_client import AgentCoreHTTPClient


@pytest.fixture
def mock_http_client():
    """Mock AgentCoreHTTPClient"""
    client = Mock(spec=AgentCoreHTTPClient)
    client.invoke_agent = AsyncMock()
    return client


@pytest.fixture
def mock_context():
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
def mock_event_queue():
    """Mock A2A event queue"""
    queue = Mock()
    queue.enqueue_event = AsyncMock()
    return queue


@pytest.fixture
def executor(mock_http_client):
    """Create AgentCoreExecutor instance"""
    return AgentCoreExecutor(mock_http_client, "test-agent-id")


class TestAgentCoreExecutor:
    """Test cases for AgentCoreExecutor"""
    
    def test_init(self, mock_http_client):
        """Test executor initialization"""
        executor = AgentCoreExecutor(mock_http_client, "test-agent")
        
        assert executor.http_client == mock_http_client
        assert executor.agent_id == "test-agent"
    
    @pytest.mark.asyncio
    async def test_execute_success(self, executor, mock_http_client, mock_context, mock_event_queue):
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
    async def test_execute_complex_response(self, executor, mock_http_client, mock_context, mock_event_queue):
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
    
    @pytest.mark.asyncio
    async def test_execute_malformed_response(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test execution with malformed response"""
        # Mock malformed response
        mock_http_client.invoke_agent.return_value = {"unexpected": "format"}
        
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify fallback to string representation
        call_args = mock_event_queue.enqueue_event.call_args[0][0]
        assert "unexpected" in call_args.parts[0].root.text
    
    @pytest.mark.asyncio
    async def test_execute_missing_message_parts(self, executor, mock_http_client, mock_event_queue):
        """Test execution with missing message parts"""
        # Mock context without message parts
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
        
        # Verify empty string was passed as prompt
        mock_http_client.invoke_agent.assert_called_once_with("test-agent-id", "")
    
    @pytest.mark.asyncio
    async def test_execute_http_client_error(self, executor, mock_http_client, mock_context, mock_event_queue):
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
    async def test_cancel(self, executor, mock_context, mock_event_queue):
        """Test cancel method (no-op for AgentCore)"""
        # Cancel should not raise any exceptions
        await executor.cancel(mock_context, mock_event_queue)
        
        # No events should be enqueued for cancel
        mock_event_queue.enqueue_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_context_without_message(self, executor, mock_http_client, mock_event_queue):
        """Test execution with context that has no message"""
        context = Mock()
        context.task_id = "test-task-id"
        context.message = Mock()
        context.message.parts = []
        context.message.contextId = "test-context-id"
        
        mock_http_client.invoke_agent.return_value = {
            "result": {
                "role": "assistant",
                "content": [{"text": "Response"}]
            }
        }
        
        await executor.execute(context, mock_event_queue)
        
        # Should handle empty message gracefully
        mock_http_client.invoke_agent.assert_called_once_with("test-agent-id", "")
        mock_event_queue.enqueue_event.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_execute_generates_unique_message_ids(self, executor, mock_http_client, mock_context, mock_event_queue):
        """Test that each execution generates unique message IDs"""
        mock_http_client.invoke_agent.return_value = {
            "result": {
                "role": "assistant",
                "content": [{"text": "Response"}]
            }
        }
        
        # Execute twice
        await executor.execute(mock_context, mock_event_queue)
        await executor.execute(mock_context, mock_event_queue)
        
        # Verify both calls generated messages
        assert mock_event_queue.enqueue_event.call_count == 2
        
        # Get message IDs
        call1_message = mock_event_queue.enqueue_event.call_args_list[0][0][0]
        call2_message = mock_event_queue.enqueue_event.call_args_list[1][0][0]
        
        # Message IDs should be different
        assert call1_message.messageId != call2_message.messageId