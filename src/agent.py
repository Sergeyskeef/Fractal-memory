"""
FractalAgent — главный фасад для AI-агента с фрактальной памятью.

Объединяет:
- FractalMemory для хранения
- HybridRetriever для умного поиска
- ReasoningBank для самообучения
- LLM для генерации ответов
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.infrastructure.rate_limiter import RateLimiter, rate_limit
from src.infrastructure.metrics import (
    memory_size,
    retrieval_latency,
    tokens_per_query,
    tokens_used,
)

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Состояние агента."""
    IDLE = "idle"
    THINKING = "thinking"
    RESPONDING = "responding"
    LEARNING = "learning"
    ERROR = "error"


@dataclass
class ChatMessage:
    """Сообщение в чате."""
    role: str  # "user" или "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Ответ агента с метаданными."""
    content: str
    context_used: List[Dict] = field(default_factory=list)
    strategies_used: List[str] = field(default_factory=list)
    memory_stats: Dict = field(default_factory=dict)
    processing_time_ms: float = 0.0


class FractalAgent:
    """
    AI-агент с фрактальной памятью.
    
    Использует иерархическую память (L0-L3) для хранения контекста,
    гибридный поиск для извлечения релевантной информации,
    и самообучение на основе опыта.
    
    Example:
        ```python
        agent = FractalAgent(config)
        await agent.initialize()
        
        response = await agent.chat("Привет! Меня зовут Сергей")
        print(response.content)
        
        await agent.close()
        ```
    """
    
    DEFAULT_CONFIG = {
        # Memory
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        # neo4j_password должен быть передан явно (безопасность)
        "redis_url": "redis://localhost:6379",
        
        # LLM
        "openai_api_key": None,  # Из env
        "model": "gpt-5-mini",
        "max_tokens": 5000,  # Увеличено: gpt-5-nano использует reasoning tokens, нужно больше места
        # "temperature": 0.7,  # Убрано - gpt-5-nano-2025-08-07 не поддерживает, использует дефолт 1
        
        # Retrieval
        "retrieval_limit": 5,
        "retrieval_weights": {
            "vector": 0.5,
            "keyword": 0.3,
            "graph": 0.2,
        },
        "llm_requests_per_minute": 60,
        
        # Agent
        "system_prompt": """
You are Mark, an intelligent AI partner.
Your goal is to be a thoughtful listener and a strategic partner.

CORE BEHAVIORS:

1. **Mirror the User's Intent:**
   - If the user is sharing, telling a story, or stating a fact -> **LISTEN**, briefly acknowledge, and react exactly as a real person would.
   - If the user asks a question -> Answer precisely and to the point.
   - If the user explicitly asks for help -> Be proactive and offer solutions.

2. **Natural Memory usage:**
   - NEVER say "I remember you said...".
   - Simply weave the knowledge from context into your response naturally, just like a human friend who knows you would.

3. **Communication Style:**
   - Concise, natural, no fluff.
   - NO bullet points for casual chit-chat.
   - NO checklists unless explicitly requested.
   - Avoid generic phrases like "How can I help you today?" in the middle of a conversation.
   - Example: If the user says "I go to the BMX track on Wednesdays", reply simply: "Cool, noted."

Your personality is calm, professional, and attentive.
""",
        
        "save_all_messages": True,
        "learn_from_interactions": True,
    }
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        memory: Optional["FractalMemory"] = None,
        retriever: Optional["HybridRetriever"] = None,
        reasoning: Optional["ReasoningBank"] = None,
        **kwargs
    ):
        """
        Инициализировать агента.
        
        Args:
            config: Конфигурация (опционально, используются defaults)
            memory: Готовый экземпляр FractalMemory (опционально)
            retriever: Готовый экземпляр HybridRetriever (опционально)
            reasoning: Готовый экземпляр ReasoningBank (опционально)
            **kwargs: Дополнительные параметры конфигурации (для обратной совместимости)
        
        Note:
            Если передаются готовые компоненты (memory, retriever, reasoning),
            они будут использованы вместо создания новых. Это полезно для тестов
            и когда нужно переиспользовать существующие подключения.
        """
        # Merge config with kwargs for backward compatibility
        merged_config = {**self.DEFAULT_CONFIG, **(config or {}), **kwargs}
        self.config = merged_config
        
        # User identity
        self.user_id = self.config.get("user_id", "default")
        self.user_name = self.config.get("user_name", "Пользователь")
        self.agent_name = self.config.get("agent_name", "Ассистент")
        
        # User context (загружается при старте)
        self.user_context: Dict[str, Any] = {}
        
        # Компоненты (инициализируются в initialize() или используются предоставленные)
        self.memory = memory
        self.retriever = retriever
        self.reasoning = reasoning
        self.llm_client = None
        
        # Track component ownership for proper cleanup
        self._owns_memory = memory is None
        self._owns_retriever = retriever is None
        self._owns_reasoning = reasoning is None
        
        # Rate limiter
        self.llm_rate_limiter: Optional[RateLimiter] = None
        rpm = self.config.get("llm_requests_per_minute")
        if rpm:
            try:
                rpm_value = int(rpm)
                if rpm_value > 0:
                    self.llm_rate_limiter = RateLimiter(rate=rpm_value, per_seconds=60)
            except Exception:
                logger.warning("Invalid llm_requests_per_minute=%s, rate limiting disabled", rpm)
        
        # Состояние
        self.state = AgentState.IDLE
        self.conversation_history: List[ChatMessage] = []
        self._initialized = False
        
        # Log if using provided components
        if memory is not None:
            logger.info("FractalAgent initialized with provided FractalMemory instance")
        if retriever is not None:
            logger.info("FractalAgent initialized with provided HybridRetriever instance")
        if reasoning is not None:
            logger.info("FractalAgent initialized with provided ReasoningBank instance")
    
    async def initialize(self) -> None:
        """
        Инициализировать все компоненты.
        
        Должен быть вызван перед использованием агента.
        """
        if self._initialized:
            return
        
        logger.info("Initializing FractalAgent...")
        
        try:
            # Передать user_id в память
            self.config["user_id"] = self.user_id
            
            # 1. Инициализировать память (или использовать предоставленную)
            if self.memory is None:
                from src.core.memory import FractalMemory
                self.memory = FractalMemory(self.config)
                await self.memory.initialize()
                logger.info("FractalMemory initialized (created new)")
            else:
                logger.info("Using provided FractalMemory instance")
                # Ensure memory is initialized
                if not getattr(self.memory, '_initialized', False):
                    await self.memory.initialize()
                    logger.info("Provided FractalMemory initialized")
            
            # 2. Инициализировать retriever (или использовать предоставленный)
            if self.retriever is None:
                from src.core.retrieval import HybridRetriever
                self.retriever = HybridRetriever(
                    self.memory.graphiti,  # Используем GraphitiStore из memory
                    user_id=self.user_id,
                    weights=self.config.get("retrieval_weights"),
                )
                logger.info("HybridRetriever initialized (created new)")
            else:
                logger.info("Using provided HybridRetriever instance")
            
            # 3. Инициализировать ReasoningBank (или использовать предоставленный)
            if self.reasoning is None:
                from src.core.reasoning import ReasoningBank
                # Используем GraphitiStore из memory вместо создания нового драйвера
                self.reasoning = ReasoningBank(self.memory.graphiti, self.user_id)
                await self.reasoning.initialize()
                logger.info("ReasoningBank initialized (created new)")
            else:
                logger.info("Using provided ReasoningBank instance")
                # Ensure reasoning is initialized
                if not getattr(self.reasoning, '_initialized', False):
                    await self.reasoning.initialize()
                    logger.info("Provided ReasoningBank initialized")
            
            # 4. Инициализировать LLM клиент
            await self._init_llm_client()
            logger.info("LLM client initialized")
            
            # 5. Загрузить контекст пользователя
            await self._load_user_context()
            
            self._initialized = True
            self.state = AgentState.IDLE
            logger.info(f"FractalAgent fully initialized for user {self.user_id}")
            
        except Exception as e:
            self.state = AgentState.ERROR
            component = self._identify_failed_component(e)
            logger.error(
                f"Failed to initialize agent at component: {component}",
                extra={
                    "component": component,
                    "error": str(e),
                    "user_id": self.user_id,
                },
                exc_info=True
            )
            raise RuntimeError(
                f"FractalAgent initialization failed at component: {component}. "
                f"Error: {str(e)}"
            ) from e
    
    def _identify_failed_component(self, error: Exception) -> str:
        """Identify which component failed based on error."""
        error_str = str(error).lower()
        
        if "neo4j" in error_str or "graphiti" in error_str:
            return "GraphitiStore (Neo4j connection)"
        elif "redis" in error_str:
            return "RedisMemoryStore (Redis connection)"
        elif "openai" in error_str or "api key" in error_str:
            return "LLM Client (OpenAI)"
        elif "memory" in error_str:
            return "FractalMemory"
        elif "retriever" in error_str:
            return "HybridRetriever"
        elif "reasoning" in error_str:
            return "ReasoningBank"
        else:
            return "Unknown component"
    
    async def _init_llm_client(self) -> None:
        """Инициализировать LLM клиент."""
        try:
            from openai import AsyncOpenAI
            import httpx
            
            api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("No OpenAI API key found, LLM features disabled")
                self.llm_client = None
                return
            
            # Настройка таймаутов для httpx клиента
            # connect: время на установку соединения
            # read: время на чтение ответа (критично для LLM)
            # write: время на отправку запроса
            # pool: время на получение соединения из пула
            timeout = httpx.Timeout(
                connect=10.0,  # 10 секунд на подключение
                read=50.0,     # 50 секунд на чтение ответа (увеличено для gpt-5-nano с reasoning)
                write=10.0,    # 10 секунд на отправку
                pool=5.0       # 5 секунд на получение соединения
            )
            
            self.llm_client = AsyncOpenAI(
                api_key=api_key,
                timeout=timeout,
                max_retries=2  # Максимум 2 попытки при ошибках
            )
            logger.info("LLM client initialized with timeouts: connect=10s, read=30s")
        except ImportError:
            logger.warning("openai package not installed, LLM features disabled")
            self.llm_client = None
    
    async def _load_user_context(self) -> None:
        """Загрузить известные факты о пользователе."""
        try:
            # Сначала из Redis (L0/L1)
            redis_facts = []
            if self.memory and self.memory.redis_store:
                redis_facts = await self.memory.redis_store.search_l0_l1(
                    self.user_name, limit=5
                )
            
            # Затем из Neo4j (L2)
            neo4j_facts = []
            if self.memory and self.memory.graphiti:
                try:
                    user_tag = f"[user:{self.user_id}]"
                    neo4j_results = await self.memory.graphiti.execute_cypher(
                        """
                        MATCH (ep:Episodic)
                        WHERE ep.content CONTAINS $user_tag
                        RETURN ep.content as content
                        ORDER BY ep.created_at DESC
                        LIMIT 10
                        """,
                        {"user_tag": user_tag}
                    )
                    neo4j_facts = [r.get("content", "") for r in (neo4j_results or [])]
                except Exception as e:
                    logger.warning(f"Failed to load Neo4j facts: {e}")
            
            self.user_context = {
                "user_id": self.user_id,
                "user_name": self.user_name,
                "agent_name": self.agent_name,
                "redis_facts": [f.get("content", "") for f in redis_facts],
                "neo4j_facts": neo4j_facts,
            }
            
            total_facts = len(redis_facts) + len(neo4j_facts)
            logger.info(f"Loaded user context: {total_facts} facts")
            
        except Exception as e:
            logger.warning(f"Failed to load user context: {e}")
            self.user_context = {
                "user_id": self.user_id,
                "user_name": self.user_name,
                "agent_name": self.agent_name,
            }
    
    def _build_system_prompt(self) -> str:
        """Построить системный промпт с контекстом."""
        prompt = f"""Ты — {self.agent_name}, AI-ассистент с долговременной памятью.
Ты помнишь предыдущие разговоры и можешь учиться на опыте.

ТВОЯ ИДЕНТИЧНОСТЬ:
- Твоё имя: {self.agent_name}
- Имя пользователя: {self.user_name}
- Ты создан {self.user_name} как помощник и партнёр
"""
        
        # Добавить известные факты
        all_facts = (
            self.user_context.get("redis_facts", []) +
            self.user_context.get("neo4j_facts", [])
        )
        
        if all_facts:
            prompt += "\nИЗВЕСТНЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ:\n"
            for fact in all_facts[:5]:
                prompt += f"- {fact[:200]}\n"
        
        prompt += """
ИНСТРУКЦИИ:
- Обращайся к пользователю по имени
- Помни свою идентичность
- Используй информацию из памяти в ответах
- НЕ спрашивай пользователя, нужно ли запомнить информацию - ты запоминаешь всё автоматически
- НЕ предлагай "запомнить" или "сохранить" факты - это происходит автоматически в фоне
- Просто общайся естественно, как собеседник, используя информацию из памяти когда она релевантна
"""
        
        return prompt
    
    async def chat(
        self,
        message: str,
        metadata: Optional[Dict] = None,
    ) -> AgentResponse:
        """
        Обработать сообщение пользователя.
        
        Args:
            message: Сообщение пользователя
            metadata: Дополнительные метаданные
        
        Returns:
            AgentResponse с ответом и метаданными
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = datetime.now()
        self.state = AgentState.THINKING
        
        try:
            # 1. Сохранить сообщение пользователя
            user_message = ChatMessage(
                role="user",
                content=message,
                metadata=metadata or {},
            )
            self.conversation_history.append(user_message)
            
            # 2. Найти релевантный контекст
            context = await self._retrieve_context(message)
            
            # 3. Получить релевантные стратегии
            strategies = await self._get_strategies(message)
            
            # 4. Сгенерировать ответ
            self.state = AgentState.RESPONDING
            response_text = await self._generate_response(
                message, context, strategies
            )
            
            # 5. Сохранить в память (асинхронно, не блокируем ответ)
            # Graphiti add_episode может занимать 10-16 секунд, поэтому запускаем в фоне
            if self.config.get("save_all_messages", True):
                # Создаём задачу, но не ждём её завершения
                asyncio.create_task(self._save_to_memory(message, response_text, metadata))
                # Обновляем метрики синхронно (быстро)
                self._update_memory_metrics()
            
            # 6. Записать опыт для обучения (тоже асинхронно)
            if self.config.get("learn_from_interactions", True):
                self.state = AgentState.LEARNING
                # Создаём задачу, но не ждём её завершения
                asyncio.create_task(self._log_experience(message, response_text, context, next_user_message=None))
            
            # 7. Добавить ответ в историю
            assistant_message = ChatMessage(
                role="assistant",
                content=response_text,
                metadata={"context_count": len(context)},
            )
            self.conversation_history.append(assistant_message)
            
            # Собрать статистику
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            memory_stats = await self.get_stats()
            
            self.state = AgentState.IDLE
            
            return AgentResponse(
                content=response_text,
                context_used=[
                    {"content": c.content[:100], "score": c.score, "source": c.source}
                    for c in context[:5]
                ],
                strategies_used=[s.description[:50] for s in strategies[:3]] if strategies else [],
                memory_stats=memory_stats,
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Chat failed: {e}")
            raise
    
    async def _retrieve_context(self, query: str) -> List:
        """Найти релевантный контекст через HybridRetriever."""
        try:
            limit = self.config.get("retrieval_limit", 5)
            start = time.perf_counter()

            context_results: List = []

            # L0: последние 15 сырых сообщений из Redis
            if self.memory and self.memory.redis_store:
                try:
                    l0_items = await self.memory.redis_store.l0_get_recent(15)
                    from src.core.retrieval import RetrievalResult
                    for item in l0_items:
                        context_results.append(
                            RetrievalResult(
                                content=item.get("content", ""),
                                score=item.get("importance", 0.5),
                                source="l0_raw",
                                metadata={"timestamp": item.get("timestamp")},
                                episode_id=item.get("stream_id"),
                            )
                        )
                except Exception as e:
                    logger.warning(f"L0 context fetch failed: {e}")

                # L1: последние 3 саммари
                try:
                    l1_summaries = await self.memory.redis_store.l1_get_recent_summaries(3)
                    from src.core.retrieval import RetrievalResult
                    for item in l1_summaries:
                        context_results.append(
                            RetrievalResult(
                                content=item.get("summary", ""),
                                score=item.get("importance", 0.6),
                                source="l1_summary",
                                metadata={"created_at": item.get("created_at"), "session_id": item.get("session_id")},
                                episode_id=item.get("session_id"),
                            )
                        )
                except Exception as e:
                    logger.warning(f"L1 summary fetch failed: {e}")

            # Решаем лимит для L2 в зависимости от наличия L0/L1
            l2_limit = limit
            if len(context_results) >= 3:
                l2_limit = max(1, limit - 2)

            # L2: Graphiti через HybridRetriever
            graph_results = await self.retriever.search(query, limit=l2_limit)
            context_results.extend(graph_results)

            duration = time.perf_counter() - start
            try:
                retrieval_latency.labels("hybrid_search").observe(duration)
            except Exception:
                pass
            logger.debug(f"Retrieved context: l0/l1={len(context_results)-len(graph_results)}, l2={len(graph_results)}")
            return context_results
        except Exception as e:
            logger.warning(f"Context retrieval failed: {e}")
            return []
    
    async def _get_strategies(self, query: str) -> List:
        """Получить релевантные стратегии из ReasoningBank."""
        try:
            if not self.reasoning:
                logger.debug("ReasoningBank not available")
                return []
            task_type = self._classify_task(query)
            logger.debug(f"Getting strategies for task_type={task_type}, query={query[:50]}")
            strategies = await self.reasoning.get_strategies(
                task_type=task_type,
                limit=3,
            )
            logger.info(f"Found {len(strategies)} strategies for task_type={task_type}")
            if strategies:
                for s in strategies:
                    logger.debug(f"  - {s.description[:50]}... (confidence: {s.success_rate or 0.0:.2f})")
            return strategies
        except Exception as e:
            logger.warning(f"Strategy retrieval failed: {e}", exc_info=True)
            return []
    
    def _classify_task(self, message: str) -> str:
        """Простая классификация типа задачи."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["код", "python", "функци", "программ"]):
            return "coding"
        elif any(word in message_lower for word in ["напиши", "создай", "сгенерируй"]):
            return "generation"
        elif any(word in message_lower for word in ["объясни", "почему", "как работает"]):
            return "explanation"
        elif any(word in message_lower for word in ["найди", "поиск", "где"]):
            return "search"
        elif any(word in message_lower for word in ["помнишь", "говорил", "раньше"]):
            return "memory_recall"
        else:
            return "general"
    
    async def _generate_response(
        self,
        message: str,
        context: List,
        strategies: List,
    ) -> str:
        """Сгенерировать ответ с помощью LLM."""
        if not self.llm_client:
            logger.warning("LLM client not available, using fallback")
            return self._fallback_response(message, context)
        
        # Построить промпт с контекстом
        system_prompt = self._build_system_prompt()
        
        # Добавить контекст из памяти (ограничиваем размер)
        if context:
            context_items = []
            total_context_chars = 0
            max_context_chars = 3000  # ~750 токенов для контекста
            
            for c in context[:5]:
                # Ограничиваем длину каждого элемента контекста
                content = c.content[:400] if len(c.content) > 400 else c.content  # Было без ограничения
                context_item = f"[Память, релевантность {c.score:.2f}]: {content}"
                if total_context_chars + len(context_item) > max_context_chars:
                    break
                context_items.append(context_item)
                total_context_chars += len(context_item)
            
            if context_items:
                context_text = "\n\n".join(context_items)
                system_prompt += f"\n\nРелевантный контекст из памяти:\n{context_text}"
        
        # Добавить стратегии с confidence и рекомендациями
        if strategies:
            strategies_text = "\n".join([
                f"- {s.description or 'Unknown'} (Confidence: {s.success_rate or 0.0:.2f}, Used: {s.usage_count or 0}x)"
                for s in strategies[:3]
            ])
            best_strategy = strategies[0] if strategies else None
            if best_strategy:
                desc = best_strategy.description or "Unknown strategy"
                conf = best_strategy.success_rate or 0.0
                usage = best_strategy.usage_count or 0
                system_prompt += f"\n\n🎯 РЕКОМЕНДУЕМАЯ СТРАТЕГИЯ: {desc}"
                system_prompt += f"\n   Confidence: {conf:.2f} | Usage: {usage} раз"
                logger.info(f"📌 Using strategy in prompt: {desc} (confidence: {conf:.2f})")
            system_prompt += f"\n\n📚 Другие успешные стратегии:\n{strategies_text}"
        
        # Ограничиваем размер system_prompt (gpt-5-nano имеет ограничения)
        # Примерно 1 токен = 4 символа, лимит промпта для gpt-5-nano ~8000 токенов
        # Оставляем запас для reasoning tokens (200-400) и completion (5000)
        max_system_prompt_chars = 20000  # ~5000 токенов для system prompt
        if len(system_prompt) > max_system_prompt_chars:
            logger.warning(f"System prompt too long ({len(system_prompt)} chars), truncating to {max_system_prompt_chars}")
            system_prompt = system_prompt[:max_system_prompt_chars] + "... [truncated]"
        
        # Финальное логирование промпта (последние 500 символов для проверки стратегий)
        logger.info(f"🛠️ FINAL SYSTEM PROMPT (snippet): {system_prompt[-500:]}")
        estimated_system_tokens = int(len(system_prompt) / 2.5)  # Для русского текста
        logger.info(f"📏 System prompt size: {len(system_prompt)} chars (~{estimated_system_tokens} tokens)")
        
        # Построить сообщения для LLM
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавить последние N сообщений из истории (ограничиваем чтобы не превысить лимит)
        # Берём только последние 3 сообщения (было 5) чтобы оставить больше места для reasoning
        recent_history = self.conversation_history[-3:]
        total_history_chars = 0
        max_history_chars = 2000  # ~500 токенов для истории
        
        for msg in recent_history:
            # Ограничиваем длину каждого сообщения
            content = msg.content[:300] if len(msg.content) > 300 else msg.content  # Было 500
            if total_history_chars + len(content) > max_history_chars:
                break  # Прекращаем добавлять, если превысили лимит
            messages.append({
                "role": msg.role,
                "content": content,
            })
            total_history_chars += len(content)
        
        # Текущее сообщение (ограничиваем длину)
        user_message = message[:1000] if len(message) > 1000 else message  # Ограничиваем длину сообщения пользователя
        if not recent_history or recent_history[-1].content != message:
            messages.append({"role": "user", "content": user_message})
        
        # Логируем общий размер промпта (для русского текста ~2.5 символа на токен)
        total_prompt_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_prompt_tokens = int(total_prompt_chars / 2.5)  # Более точная оценка для русского
        logger.info(f"📊 Total prompt size: {total_prompt_chars} chars (~{estimated_prompt_tokens} tokens), messages: {len(messages)}")
        
        # --- DIAGNOSTIC START: PROMPT X-RAY ---
        print("\n🔍 === PROMPT X-RAY (What LLM sees) ===")
        print(f"Total messages: {len(messages)}")
        for i, msg in enumerate(messages):
            role = msg.get("role", "UNKNOWN").upper()
            content = msg.get("content", "") or ""
            preview = content[:300] + "..." if len(content) > 300 else content
            print(f"[{i}] {role}: {preview}")
        print("🔍 =====================================\n")
        # --- DIAGNOSTIC END ---
        
        try:
            # Параметры для gpt-5-nano-2025-08-07 (не поддерживает temperature, использует max_completion_tokens)
            model = self.config.get("model", "gpt-5-nano-2025-08-07")
            
            logger.debug(f"Calling LLM with model={model}, messages_count={len(messages)}")
            
            # gpt-5-nano использует reasoning tokens, нужно больше места
            # reasoning может занять 200-400 токенов
            # ВАЖНО: gpt-5-nano имеет ограниченное контекстное окно (~8000-16000 токенов)
            # Если промпт слишком длинный, модель вернет пустую строку с finish_reason: length
            # Поэтому ограничиваем max_completion_tokens в зависимости от размера промпта
            base_max_tokens = self.config.get("max_tokens", 5000)
            
            # Оцениваем размер промпта в токенах (примерно 2.5 символа на токен для русского)
            estimated_prompt_tokens = int(sum(len(m.get("content", "")) for m in messages) / 2.5)
            
            # Если промпт уже большой, уменьшаем max_completion_tokens
            # Предполагаем, что общий лимит модели ~16000 токенов (консервативная оценка)
            # Оставляем запас для reasoning tokens (400) и overhead (500)
            max_total_tokens = 16000  # Консервативная оценка для gpt-5-nano
            available_for_completion = max_total_tokens - estimated_prompt_tokens - 400 - 500
            
            # Используем минимум из запрошенного и доступного
            max_tokens = min(base_max_tokens, max(500, available_for_completion))  # Минимум 500 токенов
            
            logger.info(f"📊 Prompt tokens (estimated): ~{estimated_prompt_tokens:.0f}, Available for completion: ~{available_for_completion:.0f}, Using max_completion_tokens: {max_tokens}")
            
            # Ограничиваем общее время выполнения запроса (таймаут на уровне asyncio)
            # Увеличено до 60 секунд, т.к. Graphiti может занимать время при сохранении
            # Но сохранение теперь асинхронное, так что основной запрос должен быть быстрее
            llm_timeout = self.config.get("llm_timeout_seconds", 60.0)  # 60 секунд общий таймаут
            
            async def _call_llm():
                if self.llm_rate_limiter:
                    async with rate_limit(self.llm_rate_limiter):
                        return await self.llm_client.chat.completions.create(
                            model=model,
                            messages=messages,
                            max_completion_tokens=max_tokens,
                        )
                else:
                    return await self.llm_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_completion_tokens=max_tokens,
                    )
            
            # Выполняем с таймаутом на уровне asyncio
            try:
                response = await asyncio.wait_for(_call_llm(), timeout=llm_timeout)
            except asyncio.TimeoutError:
                logger.error(f"LLM request timed out after {llm_timeout}s. Model: {model}")
                return "Извините, запрос занял слишком много времени. Попробуйте переформулировать вопрос или повторить попытку позже."
            
            # Детальная диагностика ответа
            logger.debug(f"LLM API response: {type(response)}, choices count: {len(response.choices) if response.choices else 0}")
            
            if not response.choices:
                logger.error(f"LLM returned no choices. Full response: {response}")
                return self._fallback_response(message, context)
            
            result = response.choices[0].message.content
            logger.info(f"LLM response received: type={type(result)}, len={len(result) if result else 0}, content={repr(result[:100]) if result else 'None'}")
            
            # Проверка на пустой ответ
            if result is None:
                logger.warning(f"LLM returned None. Model: {model}, Messages: {len(messages)}, Response object: {response}")
                return self._fallback_response(message, context)

            usage = getattr(response, "usage", None)
            total_tokens = self._usage_stat(usage, "total_tokens")
            prompt_tokens = self._usage_stat(usage, "prompt_tokens")
            completion_tokens = self._usage_stat(usage, "completion_tokens")
            if total_tokens:
                tokens_used.labels(component="llm_total").inc(total_tokens)
                tokens_per_query.observe(total_tokens)
            if prompt_tokens:
                tokens_used.labels(component="llm_prompt").inc(prompt_tokens)
            if completion_tokens:
                tokens_used.labels(component="llm_completion").inc(completion_tokens)
            
            if not result or not result.strip():
                logger.warning(f"LLM returned empty string. Model: {model}, Messages: {len(messages)}, Raw content: {repr(result)}")
                # Попробуем использовать finish_reason для диагностики
                finish_reason = getattr(response.choices[0], 'finish_reason', None)
                logger.warning(f"Finish reason: {finish_reason}")
                
                # Если finish_reason = "length", значит модель достигла лимита токенов
                # Попробуем еще раз с более коротким промптом
                if finish_reason == "length":
                    logger.warning("LLM hit token limit, trying with shorter prompt")
                    try:
                        simple_messages = [
                            {"role": "system", "content": f"Ты — {self.agent_name}. Отвечай кратко и по делу."},
                            {"role": "user", "content": message[:500]}  # Ограничиваем длину сообщения
                        ]
                        retry_response = await asyncio.wait_for(
                            self.llm_client.chat.completions.create(
                                model=model,
                                messages=simple_messages,
                                max_completion_tokens=500,  # Меньше токенов для быстрого ответа
                            ),
                            timeout=20.0
                        )
                        if retry_response.choices and retry_response.choices[0].message.content:
                            retry_result = retry_response.choices[0].message.content.strip()
                            if retry_result:
                                logger.info("Retry with shorter prompt succeeded")
                                return retry_result
                            else:
                                logger.warning("Retry returned empty string again")
                        else:
                            logger.warning("Retry response has no choices or content")
                    except Exception as retry_error:
                        logger.warning(f"Retry failed: {retry_error}", exc_info=True)
                
                # Если retry не помог, возвращаем понятное сообщение об ошибке
                return f"Сергей, я понял ваше сообщение: '{message[:100]}...'. К сожалению, сейчас у меня возникли технические проблемы с генерацией ответа. Попробуйте повторить запрос или переформулировать вопрос."
            
            return result
            
        except asyncio.TimeoutError:
            # Уже обработано выше, но на всякий случай
            logger.error(f"LLM request timed out. Model: {self.config.get('model', 'gpt-5-nano-2025-08-07')}")
            return "Извините, запрос занял слишком много времени. Попробуйте переформулировать вопрос или повторить попытку позже."
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            error_msg = str(e)
            # Обработка различных типов ошибок
            if "401" in error_msg or "authentication" in error_msg.lower():
                return "Ошибка: Неверный API ключ OpenAI. Проверьте OPENAI_API_KEY."
            if "model" in error_msg.lower() and "not found" in error_msg.lower():
                return f"Ошибка: Модель {self.config.get('model', 'gpt-5-nano-2025-08-07')} не найдена. Проверьте название модели."
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return "Извините, запрос занял слишком много времени. Попробуйте переформулировать вопрос или повторить попытку позже."
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                return "Извините, превышен лимит запросов к API. Пожалуйста, подождите немного и попробуйте снова."
            # Обработка ошибки max_tokens
            if "max_tokens" in error_msg.lower() or "output limit" in error_msg.lower() or "400" in error_msg:
                logger.warning("LLM hit max_tokens limit, trying with shorter prompt and higher limit")
                # Попробуем еще раз с упрощенным промптом и увеличенным лимитом
                try:
                    simple_messages = [
                        {"role": "system", "content": f"Ты — {self.agent_name}. Отвечай кратко и по делу."},
                        {"role": "user", "content": message[:500]}  # Ограничиваем длину сообщения
                    ]
                    retry_response = await asyncio.wait_for(
                        self.llm_client.chat.completions.create(
                            model=model,
                            messages=simple_messages,
                            max_completion_tokens=5000,  # Увеличенный лимит для retry
                        ),
                        timeout=30.0
                    )
                    if retry_response.choices and retry_response.choices[0].message.content:
                        retry_result = retry_response.choices[0].message.content.strip()
                        if retry_result:
                            logger.info("Retry with shorter prompt and higher max_tokens succeeded")
                            return retry_result
                except Exception as retry_error:
                    logger.warning(f"Retry failed: {retry_error}")
                return "Сергей, ваш запрос слишком длинный или ответ требует больше места. Попробуйте переформулировать вопрос короче или разбить на части."
            return f"Ошибка LLM: {error_msg[:200]}"

    @staticmethod
    def _usage_stat(usage: Optional[Any], field: str) -> Optional[int]:
        if usage is None:
            return None
        if hasattr(usage, field):
            return getattr(usage, field)
        if isinstance(usage, dict):
            return usage.get(field)
        return None

    def _fallback_response(self, message: str, context: List) -> str:
        """Fallback ответ когда LLM недоступен или вернул пустой ответ."""
        # Пытаемся дать более полезный ответ на основе контекста
        if context:
            context_text = context[0].content[:200] if context[0].content else ""
            return f"Сергей, я нашел в памяти: {context_text}... Но сейчас у меня возникли проблемы с генерацией ответа. Попробуйте переформулировать вопрос или повторить попытку."
        
        # Если есть история разговора, пытаемся ответить на основе последних сообщений
        if self.conversation_history:
            last_user_msg = None
            for msg in reversed(self.conversation_history):
                if msg.role == "user":
                    last_user_msg = msg.content
                    break
            
            if last_user_msg:
                return f"Сергей, я понял ваше сообщение: '{last_user_msg[:100]}...'. К сожалению, сейчас у меня возникли технические проблемы с генерацией ответа. Попробуйте повторить запрос или переформулировать вопрос."
        
        return f"Сергей, я получил ваше сообщение, но сейчас у меня возникли технические проблемы с генерацией ответа. Пожалуйста, попробуйте повторить запрос или переформулировать вопрос."

    def _update_memory_metrics(self) -> None:
        if not self.memory:
            return
        try:
            memory_size.labels(level="l0").set(len(self.memory.l0_cache))
            memory_size.labels(level="l1").set(len(self.memory.l1_cache))
        except Exception:
            # Прометей может быть не настроен — в этом случае просто пропускаем обновление
            pass
    
    async def _save_to_memory(
        self,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Сохранить обмен в память с автоматическим определением важности."""
        try:
            content = f"User: {user_message}\nAssistant: {assistant_response}"
            # Ограничиваем длину контента чтобы не перегружать память
            if len(content) > 2000:
                content = content[:2000] + "..."
            
            # Определить важность на основе содержания
            importance = self._calculate_importance(user_message, assistant_response)
            
            # Сохранить в память через remember() - это сохранит в L0, затем консолидация перенесёт в L1/L2
            # НЕ сохраняем напрямую в L2, чтобы избежать дублирования и дать системе правильно распределить данные
            await self.memory.remember(
                content=content,
                importance=importance,
                metadata={
                    "type": "conversation",
                    "user_message": user_message[:200],
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {}),
                },
            )
            
            logger.info(f"Saved conversation with importance={importance:.2f} (will consolidate to L1/L2 automatically)")
        except Exception as e:
            # Не критично если сохранение не удалось - просто логируем
            logger.warning(f"Failed to save to memory (non-critical): {e}")
    
    def _calculate_importance(self, user_message: str, assistant_response: str) -> float:
        """Рассчитать важность сообщения."""
        importance = 0.5  # Базовая важность
        
        user_lower = user_message.lower()
        
        # Персональная информация — критически важна
        personal_keywords = [
            "меня зовут", "мое имя", "я ", "моя ", "мой ",
            "тебя зовут", "твое имя", "ты ", "твоя ", "твой ",
            "создатель", "разработчик", "автор",
        ]
        if any(kw in user_lower for kw in personal_keywords):
            importance = max(importance, 0.9)
        
        # Явные команды запомнить
        remember_keywords = [
            "запомни", "сохрани", "не забудь", "важно",
            "на долгий срок", "навсегда", "помни",
        ]
        if any(kw in user_lower for kw in remember_keywords):
            importance = max(importance, 0.95)
        
        # Факты и определения
        fact_keywords = [
            "это ", "является", "значит", "означает",
            "называется", "определение", "суть",
        ]
        if any(kw in user_lower for kw in fact_keywords):
            importance = max(importance, 0.75)
        
        # Проекты и задачи
        project_keywords = [
            "проект", "задача", "цель", "план",
            "работаю над", "делаю", "разрабатываю",
        ]
        if any(kw in user_lower for kw in project_keywords):
            importance = max(importance, 0.8)
        
        return importance
    
    def _judge_outcome(self, next_user_message: Optional[str]) -> "Outcome":
        """
        Эвристический Judge: отрицательные триггеры -> FAIL, позитив -> SUCCESS (verified),
        иначе UNKNOWN (unverified).
        """
        from src.core.types import Outcome
        if not next_user_message:
            return Outcome.UNKNOWN
        text = next_user_message.lower()
        negative_triggers = ["wrong", "error", "bug", "fail", "no", "не работает", "ошибка", "неверно"]
        positive_triggers = ["ok", "thanks", "спасибо", "good", "great", "дальше"]
        if any(t in text for t in negative_triggers):
            return Outcome.FAILURE
        if any(t in text for t in positive_triggers):
            return Outcome.SUCCESS
        return Outcome.UNKNOWN
    
    async def _save_to_l2_directly(
        self,
        content: str,
        importance: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Сохранить напрямую в L2 (Neo4j) для критически важных данных."""
        try:
            # Сохранить в L2 через GraphitiStore (новый API)
            if self.memory and self.memory.graphiti:
                await self.memory.graphiti.add_episode(
                    content=content,
                    importance=importance,
                    source="direct_save"
                )
                logger.info(f"Saved directly to L2 via GraphitiStore")
            else:
                logger.warning("GraphitiStore not available for direct save")
        except Exception as e:
            logger.warning(f"Failed to save directly to L2: {e}")
    
    async def _log_experience(
        self,
        message: str,
        response: str,
        context: List,
        next_user_message: Optional[str] = None,
    ) -> None:
        """
        Записать опыт для самообучения.
        
        Использует лучшую стратегию, если она была применена, и логирует результат.
        По умолчанию считаем успешным (можно улучшить, добавив оценку качества ответа).
        """
        try:
            if not self.reasoning:
                return
            
            task_type = self._classify_task(message)
            
            # Получаем стратегию, которая была использована (если есть)
            strategies = await self._get_strategies(message)
            strategy_used = strategies[0].description if strategies and len(strategies) > 0 else None
            
            from src.core.types import Outcome
            outcome = self._judge_outcome(next_user_message)
            context_snapshot = response[:500]
            await self.reasoning.log_experience(
                task_type=task_type,
                query=message[:200],
                strategy_used=strategy_used or "default",
                outcome=outcome,
                feedback=f"Response length: {len(response)} chars, context items: {len(context)}",
                context_episode_id=getattr(self.memory, "last_episode_id", None) if self.memory else None,
                context_snapshot=context_snapshot,
            )
            logger.info(f"📝 Logged experience: task_type={task_type}, strategy={strategy_used}, outcome={outcome.value}")
        except Exception as e:
            # Не критично если логирование не удалось - просто логируем
            logger.warning(f"Failed to log experience (non-critical): {e}")
    
    async def provide_feedback(
        self,
        positive: bool,
        message_index: int = -1,
    ) -> None:
        """
        Предоставить обратную связь на ответ.
        
        Args:
            positive: True если ответ был полезен
            message_index: Индекс сообщения (-1 = последнее)
        """
        try:
            if not self.reasoning:
                return
            # Найти соответствующее сообщение
            if abs(message_index) > len(self.conversation_history):
                return
            
            msg = self.conversation_history[message_index]
            if msg.role != "assistant":
                # Найти предыдущий ответ ассистента
                for i in range(message_index, -len(self.conversation_history) - 1, -1):
                    if self.conversation_history[i].role == "assistant":
                        msg = self.conversation_history[i]
                        break
            await self.reasoning.add_experience(
                context=f"response_preview={msg.content[:100]}",
                action="user_feedback",
                outcome=positive,
            )
            
            logger.info(f"Feedback recorded: {'positive' if positive else 'negative'}")
            
        except Exception as e:
            logger.warning(f"Failed to record feedback: {e}")
    
    async def get_stats(self) -> Dict:
        """Получить статистику памяти и агента."""
        stats = {
            "state": self.state.value,
            "conversation_length": len(self.conversation_history),
            "initialized": self._initialized,
        }
        
        if self.memory and self._initialized:
            try:
                memory_stats = await self.memory.get_stats()
                stats["memory"] = memory_stats
            except Exception as e:
                stats["memory"] = {"error": str(e)}
        
        if self.reasoning and self._initialized:
            try:
                stats["strategies_count"] = len(self.reasoning.strategies)
                stats["experience_buffer"] = len(self.reasoning.experience_buffer)
            except Exception:
                pass
        
        self._update_memory_metrics()
        return stats
    
    async def load_file(self, filepath: str, source: Optional[str] = None) -> Dict:
        """
        Загрузить файл в память.
        
        Args:
            filepath: Путь к файлу
            source: Описание источника (опционально)
        
        Returns:
            Статистика загрузки
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбить на чанки если большой файл
            chunks = self._split_into_chunks(content, max_size=2000)
            
            for i, chunk in enumerate(chunks):
                await self.memory.remember(
                    content=chunk,
                    importance=0.7,
                    metadata={
                        "type": "file",
                        "source": source or filepath,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                )
            
            return {
                "success": True,
                "filepath": filepath,
                "chunks_created": len(chunks),
                "total_chars": len(content),
            }
            
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _split_into_chunks(self, text: str, max_size: int = 2000) -> List[str]:
        """Разбить текст на чанки."""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def clear_history(self) -> None:
        """Очистить историю разговора (не память!)."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    async def close(self) -> None:
        """
        Закрыть все соединения.
        
        Note:
            Закрываются только компоненты, созданные агентом (owned components).
            Компоненты, переданные извне, не закрываются.
        """
        logger.info("Closing FractalAgent...")
        
        # Only close components we own
        if self._owns_memory and self.memory:
            await self.memory.close()
            logger.info("Closed owned FractalMemory")
        
        if self._owns_reasoning and self.reasoning:
            if hasattr(self.reasoning, 'close'):
                await self.reasoning.close()
                logger.info("Closed owned ReasoningBank")
        
        # Retriever typically doesn't need explicit close as it shares GraphitiStore
        # but we log for completeness
        if self._owns_retriever and self.retriever:
            logger.info("HybridRetriever cleanup (shares GraphitiStore, no explicit close needed)")
        
        self._initialized = False
        self.state = AgentState.IDLE
        logger.info("FractalAgent closed")


# Convenience функция
async def create_agent(config: Optional[Dict] = None) -> FractalAgent:
    """Создать и инициализировать агента."""
    agent = FractalAgent(config)
    await agent.initialize()
    return agent



