"""
Unit tests для FractalAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agent import FractalAgent, AgentState, ChatMessage, AgentResponse


class TestFractalAgent:
    """Тесты для FractalAgent."""
    
    @pytest.fixture
    def config(self):
        return {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "neo4j_password": "test",
            "openai_api_key": "test-key",
            "save_all_messages": True,
            "learn_from_interactions": True,
        }
    
    @pytest.fixture
    def agent(self, config):
        return FractalAgent(config)
    
    def test_init_default_config(self):
        """Агент инициализируется с дефолтным конфигом."""
        agent = FractalAgent()
        
        assert agent.config is not None
        assert "neo4j_uri" in agent.config
        assert agent.state == AgentState.IDLE
        assert not agent._initialized
    
    def test_init_custom_config(self, config):
        """Агент принимает кастомный конфиг."""
        agent = FractalAgent(config)
        
        assert agent.config["openai_api_key"] == "test-key"
    
    @pytest.mark.asyncio
    async def test_initialize(self, agent):
        """Инициализация загружает все компоненты."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            # Настроить моки
            mock_memory = AsyncMock()
            mock_memory.graph = MagicMock()
            MockMemory.return_value = mock_memory
            
            MockRetriever.return_value = MagicMock()
            
            mock_reasoning = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            
            assert agent._initialized
            assert agent.state == AgentState.IDLE
            MockMemory.assert_called_once()
            mock_memory.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_without_llm(self, agent):
        """Chat работает без LLM (fallback)."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            # Настроить моки
            mock_memory = AsyncMock()
            mock_memory.graphiti = MagicMock()
            mock_memory.remember = AsyncMock()
            mock_memory.get_stats = MagicMock(return_value={"l0_count": 0})
            MockMemory.return_value = mock_memory
            
            mock_retriever = MagicMock()
            mock_retriever.search = AsyncMock(return_value=[])
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.get_strategies = AsyncMock(return_value=[])
            mock_reasoning.add_experience = AsyncMock()
            mock_reasoning.strategies = []
            mock_reasoning.experience_buffer = []
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            agent.llm_client = None  # Без LLM
            
            response = await agent.chat("Тест")
            
            assert isinstance(response, AgentResponse)
            assert response.content  # Есть fallback ответ
    
    @pytest.mark.asyncio
    async def test_chat_saves_to_history(self, agent):
        """Chat сохраняет сообщения в историю."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever') as MockRetriever, \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_memory = AsyncMock()
            mock_memory.graphiti = MagicMock()
            mock_memory.remember = AsyncMock()
            mock_memory.get_stats = MagicMock(return_value={})
            MockMemory.return_value = mock_memory
            
            mock_retriever = MagicMock()
            mock_retriever.search = AsyncMock(return_value=[])
            MockRetriever.return_value = mock_retriever
            
            mock_reasoning = AsyncMock()
            mock_reasoning.get_strategies = AsyncMock(return_value=[])
            mock_reasoning.add_experience = AsyncMock()
            mock_reasoning.strategies = []
            mock_reasoning.experience_buffer = []
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            agent.llm_client = None
            
            await agent.chat("Сообщение 1")
            await agent.chat("Сообщение 2")
            
            assert len(agent.conversation_history) == 4  # 2 user + 2 assistant
    
    def test_classify_task(self, agent):
        """Классификация задач работает."""
        assert agent._classify_task("напиши код на python") == "coding"
        assert agent._classify_task("создай документ") == "generation"
        assert agent._classify_task("объясни как работает") == "explanation"
        assert agent._classify_task("привет") == "general"
        assert agent._classify_task("ты помнишь что я говорил?") == "memory_recall"
    
    def test_split_into_chunks(self, agent):
        """Разбиение на чанки работает."""
        short_text = "Короткий текст"
        chunks = agent._split_into_chunks(short_text, max_size=100)
        assert len(chunks) == 1
        
        long_text = "Параграф 1\n\n" * 50
        chunks = agent._split_into_chunks(long_text, max_size=100)
        assert len(chunks) > 1
    
    def test_clear_history(self, agent):
        """Очистка истории работает."""
        agent.conversation_history = [
            ChatMessage(role="user", content="test"),
            ChatMessage(role="assistant", content="response"),
        ]
        
        agent.clear_history()
        
        assert len(agent.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_close(self, agent):
        """Close корректно завершает работу."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever'), \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_memory = AsyncMock()
            mock_memory.graphiti = MagicMock()
            MockMemory.return_value = mock_memory
            
            mock_reasoning = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            await agent.close()
            
            assert not agent._initialized
            mock_memory.close.assert_called_once()
            mock_reasoning.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, agent):
        """get_stats возвращает статистику."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever'), \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_memory = AsyncMock()
            mock_memory.graph = MagicMock()
            mock_memory.get_stats = MagicMock(return_value={"l0_count": 5})
            MockMemory.return_value = mock_memory
            
            mock_reasoning = AsyncMock()
            mock_reasoning.strategies = [1, 2, 3]
            mock_reasoning.experience_buffer = [1]
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            
            stats = await agent.get_stats()
            
            assert stats["initialized"] is True
            assert "memory" in stats
            assert stats["strategies_count"] == 3
    
    @pytest.mark.asyncio
    async def test_provide_feedback(self, agent):
        """Обратная связь записывается."""
        with patch('src.core.memory.FractalMemory') as MockMemory, \
             patch('src.core.retrieval.HybridRetriever'), \
             patch('src.core.reasoning.ReasoningBank') as MockReasoning:
            
            mock_memory = AsyncMock()
            mock_memory.graph = MagicMock()
            MockMemory.return_value = mock_memory
            
            mock_reasoning = AsyncMock()
            mock_reasoning.add_experience = AsyncMock()
            MockReasoning.return_value = mock_reasoning
            
            await agent.initialize()
            
            # Добавить историю
            agent.conversation_history = [
                ChatMessage(role="user", content="вопрос"),
                ChatMessage(role="assistant", content="ответ"),
            ]
            
            await agent.provide_feedback(positive=True)
            
            mock_reasoning.add_experience.assert_called_once()


class TestChatMessage:
    """Тесты для ChatMessage."""
    
    def test_create_message(self):
        msg = ChatMessage(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}


class TestAgentResponse:
    """Тесты для AgentResponse."""
    
    def test_create_response(self):
        response = AgentResponse(
            content="Test response",
            context_used=[{"content": "ctx", "score": 0.9}],
            processing_time_ms=150.5,
        )
        
        assert response.content == "Test response"
        assert len(response.context_used) == 1
        assert response.processing_time_ms == 150.5

