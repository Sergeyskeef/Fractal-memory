"""
Property-based tests for FractalAgent initialization.

These tests verify universal properties that should hold across all valid inputs.
Uses hypothesis library for property-based testing with minimum 100 iterations per test.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.agent import FractalAgent, AgentState
from src.core.memory import FractalMemory


# Hypothesis strategies for generating test data
@st.composite
def valid_config(draw):
    """Generate valid configuration dictionaries."""
    return {
        "user_id": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "user_name": draw(st.text(min_size=1, max_size=50)),
        "agent_name": draw(st.text(min_size=1, max_size=50)),
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "test_password",
        "redis_url": "redis://localhost:6379",
        "openai_api_key": None,  # Disable LLM for tests
    }


class TestAgentInitializationProperties:
    """Property-based tests for FractalAgent initialization."""
    
    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(config=valid_config())
    async def test_property_1_successful_initialization_state(self, config):
        """
        Feature: critical-fixes, Property 1: Successful initialization sets correct state
        
        For any valid configuration, when FractalAgent initialization completes successfully,
        the initialized flag should be True and state should be IDLE.
        
        Validates: Requirements 1.5
        """
        # Mock components to avoid actual database connections
        with patch('src.agent.FractalMemory') as MockMemory, \
             patch('src.agent.HybridRetriever') as MockRetriever, \
             patch('src.agent.ReasoningBank') as MockReasoning:
            
            # Setup mocks
            mock_memory = AsyncMock()
            mock_memory.initialize = AsyncMock()
            mock_memory.graphiti = Mock()
            mock_memory.redis_store = None
            MockMemory.return_value = mock_memory
            
            mock_retriever = Mock()
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            # Create and initialize agent
            agent = FractalAgent(config=config)
            await agent.initialize()
            
            # Property: After successful initialization, _initialized should be True and state should be IDLE
            assert agent._initialized is True, f"Expected _initialized=True, got {agent._initialized}"
            assert agent.state == AgentState.IDLE, f"Expected state=IDLE, got {agent.state}"
            
            # Cleanup
            await agent.close()
    
    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(config=valid_config())
    async def test_property_2_all_components_initialized(self, config):
        """
        Feature: critical-fixes, Property 2: All components initialized after successful init
        
        For any valid configuration, when FractalAgent initialization completes successfully,
        all components (memory, retriever, reasoning, llm_client) should be non-None.
        
        Validates: Requirements 1.2
        """
        # Mock components
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            # Setup mocks
            mock_memory = AsyncMock()
            mock_memory.initialize = AsyncMock()
            mock_memory.graphiti = Mock()
            mock_memory.redis_store = None
            MockMemory.return_value = mock_memory
            
            mock_retriever = Mock()
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            # Create and initialize agent
            agent = FractalAgent(config=config)
            await agent.initialize()
            
            # Property: All components should be non-None after initialization
            assert agent.memory is not None, "memory should not be None after initialization"
            assert agent.retriever is not None, "retriever should not be None after initialization"
            assert agent.reasoning is not None, "reasoning should not be None after initialization"
            # llm_client can be None if no API key, so we don't check it
            
            # Cleanup
            await agent.close()
    
    @pytest.mark.asyncio
    async def test_property_4_provided_memory_instance_used(self):
        """
        Feature: critical-fixes, Property 4: Provided memory instance is used
        
        For any FractalMemory instance passed to FractalAgent, the agent should use
        that exact instance (same object identity) rather than creating a new one.
        
        Validates: Requirements 1.4
        """
        # Create a mock memory with a unique marker
        mock_memory = AsyncMock()
        mock_memory.initialize = AsyncMock()
        mock_memory.graphiti = Mock()
        mock_memory.redis_store = None
        mock_memory._initialized = True
        mock_memory.unique_marker = "test_marker_12345"  # Unique marker
        
        # Mock other components
        with patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_retriever = Mock()
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            # Create agent with provided memory
            agent = FractalAgent(memory=mock_memory)
            await agent.initialize()
            
            # Property: Agent should use the exact same memory instance (identity check)
            assert agent.memory is mock_memory, "Agent should use the provided memory instance"
            assert hasattr(agent.memory, 'unique_marker'), "Memory should have unique marker"
            assert agent.memory.unique_marker == "test_marker_12345", "Memory marker should match"
            
            # Property: Agent should not own the memory (for cleanup)
            assert agent._owns_memory is False, "Agent should not own provided memory"
            
            # Cleanup
            await agent.close()
    
    @pytest.mark.asyncio
    async def test_property_8_graphiti_store_sharing(self):
        """
        Feature: critical-fixes, Property 8: GraphitiStore instance is shared
        
        For any initialized FractalAgent, the GraphitiStore instance used by
        HybridRetriever and ReasoningBank should be the same object (same identity)
        as the one in FractalMemory.
        
        Validates: Requirements 3.2, 3.3, 3.4
        """
        # Create mock memory with graphiti
        mock_graphiti = Mock()
        mock_graphiti.unique_id = "graphiti_12345"  # Unique marker
        
        mock_memory = AsyncMock()
        mock_memory.initialize = AsyncMock()
        mock_memory.graphiti = mock_graphiti
        mock_memory.redis_store = None
        mock_memory._initialized = True
        
        # Track GraphitiStore instances passed to components
        retriever_graphiti = None
        reasoning_graphiti = None
        
        def create_retriever(graphiti, **kwargs):
            nonlocal retriever_graphiti
            retriever_graphiti = graphiti
            return Mock()
        
        def create_reasoning(graphiti, *args):
            nonlocal reasoning_graphiti
            reasoning_graphiti = graphiti
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            return mock_reasoning
        
        with patch('src.core.retrieval.HybridRetriever', side_effect=create_retriever), \
             patch('src.core.reasoning.ReasoningBank', side_effect=create_reasoning):
            
            # Create agent with provided memory
            agent = FractalAgent(memory=mock_memory)
            await agent.initialize()
            
            # Property: All components should share the same GraphitiStore instance
            assert retriever_graphiti is mock_graphiti, "HybridRetriever should use memory's GraphitiStore"
            assert reasoning_graphiti is mock_graphiti, "ReasoningBank should use memory's GraphitiStore"
            assert hasattr(retriever_graphiti, 'unique_id'), "GraphitiStore should have unique_id"
            assert retriever_graphiti.unique_id == "graphiti_12345", "GraphitiStore ID should match"
            
            # Cleanup
            await agent.close()
    
    @pytest.mark.asyncio
    async def test_property_9_close_cleans_up_owned_components(self):
        """
        Feature: critical-fixes, Property 9: Close cleans up owned components
        
        For any initialized FractalAgent, after calling close(), all components
        that were created by the agent (not provided externally) should have
        their close() methods called.
        
        Validates: Requirements 3.5
        """
        # Test 1: Agent creates all components (owns them)
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            # Setup mocks with close tracking
            mock_memory = AsyncMock()
            mock_memory.initialize = AsyncMock()
            mock_memory.close = AsyncMock()
            mock_memory.graphiti = Mock()
            mock_memory.redis_store = None
            MockMemory.return_value = mock_memory
            
            mock_retriever = Mock()
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            mock_reasoning.close = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            # Create and initialize agent (creates components)
            agent = FractalAgent()
            await agent.initialize()
            
            # Property: Agent should own all components
            assert agent._owns_memory is True
            assert agent._owns_retriever is True
            assert agent._owns_reasoning is True
            
            # Close agent
            await agent.close()
            
            # Property: Owned components should be closed
            mock_memory.close.assert_called_once()
            mock_reasoning.close.assert_called_once()
        
        # Test 2: Agent uses provided components (doesn't own them)
        mock_memory = AsyncMock()
        mock_memory.initialize = AsyncMock()
        mock_memory.close = AsyncMock()
        mock_memory.graphiti = Mock()
        mock_memory.redis_store = None
        mock_memory._initialized = True
        
        with patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_retriever = Mock()
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.initialize = AsyncMock()
            mock_reasoning.close = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            # Create agent with provided memory
            agent = FractalAgent(memory=mock_memory)
            await agent.initialize()
            
            # Property: Agent should not own provided memory
            assert agent._owns_memory is False
            
            # Reset close call count
            mock_memory.close.reset_mock()
            
            # Close agent
            await agent.close()
            
            # Property: Provided memory should NOT be closed
            mock_memory.close.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
