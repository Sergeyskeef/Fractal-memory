"""
ReasoningBank — система самообучения на опыте.

Реализует Phase 3: хранение стратегий и опыта в Neo4j.
Использует структурированные узлы Strategy и Experience, а не JSON внутри текста.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.core.types import Outcome
from src.infrastructure.metrics import strategy_success_rate

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """Стратегия решения задач."""
    id: str
    user_id: str
    task_type: str  # coding, research, conversation, etc.
    description: str
    success_rate: float
    usage_count: int
    created_at: datetime
    updated_at: datetime


class ReasoningBank:
    """
    Хранилище стратегий и опыта.
    
    Использует отдельные узлы :Strategy и :Experience в Neo4j,
    а не парсинг JSON из Graphiti results.
    
    Args:
        graph_store: Экземпляр GraphitiStore (доступ к Neo4j через execute_cypher)
        user_id: ID пользователя для фильтрации данных
    """
    
    def __init__(self, graph_store, user_id: str):
        """
        Args:
            graph_store: Экземпляр GraphitiStore (доступ к Neo4j)
            user_id: ID пользователя
        """
        self.graph = graph_store
        self.user_id = user_id
    
    async def initialize(self) -> None:
        """Создать индексы для Strategy и Experience."""
        # Индексы создаются миграциями, но здесь можно проверить/прогреть кэш
        try:
            # Проверяем что индексы существуют (они должны быть созданы миграциями)
            await self.graph.execute_cypher("""
                SHOW INDEXES YIELD name, state
                WHERE name CONTAINS 'strategy' OR name CONTAINS 'experience'
                RETURN count(*) as count
            """)
            logger.info("ReasoningBank initialized (indices expected from migrations)")
        except Exception as e:
            logger.warning(f"Could not verify ReasoningBank indices: {e}")
    
    async def close(self) -> None:
        """Закрыть соединение (делегируется в GraphitiStore)."""
        # GraphitiStore управляет своим соединением, здесь ничего не нужно
        pass
    
    async def add_strategy(self, task_type: str, description: str,
                           initial_success: bool = True) -> str:
        """Добавить новую стратегию."""
        strategy_id = str(uuid.uuid4())
        
        await self.graph.execute_cypher("""
            CREATE (s:Strategy {
                id: $id,
                user_id: $user_id,
                task_type: $task_type,
                description: $description,
                success_rate: $success_rate,
                usage_count: 1,
                created_at: datetime(),
                updated_at: datetime()
            })
        """, {
            "id": strategy_id,
            "user_id": self.user_id,
            "task_type": task_type,
            "description": description,
            "success_rate": 1.0 if initial_success else 0.0,
        })
        
        logger.info(f"Strategy added: {task_type} -> {description[:50]}...")
        try:
            strategy_success_rate.labels(strategy_id=strategy_id).set(
                1.0 if initial_success else 0.0
            )
        except Exception:
            pass
        return strategy_id
    
    async def get_strategies(self, task_type: str = None, 
                             limit: int = 5) -> List[Strategy]:
        """Получить стратегии для типа задачи."""
        if task_type:
            results = await self.graph.execute_cypher("""
                MATCH (s:Strategy {user_id: $user_id})
                WHERE s.task_type = $task_type OR s.task_type = 'general'
                RETURN s.id as id,
                       s.user_id as user_id,
                       s.task_type as task_type,
                       s.description as description,
                       s.success_rate as success_rate,
                       s.usage_count as usage_count,
                       s.created_at as created_at,
                       s.updated_at as updated_at
                ORDER BY s.success_rate DESC, s.usage_count DESC
                LIMIT $limit
            """, {
                "user_id": self.user_id,
                "task_type": task_type,
                "limit": limit,
            })
        else:
            results = await self.graph.execute_cypher("""
                MATCH (s:Strategy {user_id: $user_id})
                RETURN s.id as id,
                       s.user_id as user_id,
                       s.task_type as task_type,
                       s.description as description,
                       s.success_rate as success_rate,
                       s.usage_count as usage_count,
                       s.created_at as created_at,
                       s.updated_at as updated_at
                ORDER BY s.success_rate DESC, s.usage_count DESC
                LIMIT $limit
            """, {
                "user_id": self.user_id,
                "limit": limit,
            })
        
        strategies = []
        for record in results:
            strategies.append(Strategy(
                id=record["id"],
                user_id=record["user_id"],
                task_type=record["task_type"],
                description=record["description"],
                success_rate=record["success_rate"],
                usage_count=record["usage_count"],
                created_at=record["created_at"],
                updated_at=record["updated_at"],
            ))
        
        return strategies
    
    async def record_outcome(self, strategy_id: str, success: bool) -> None:
        """Записать результат использования стратегии."""
        results = await self.graph.execute_cypher("""
            MATCH (s:Strategy {id: $id})
            SET s.usage_count = s.usage_count + 1,
                s.success_rate = (s.success_rate * (s.usage_count - 1) + $outcome) / s.usage_count,
                s.updated_at = datetime()
            RETURN s.success_rate AS rate
        """, {
            "id": strategy_id,
            "outcome": 1.0 if success else 0.0,
        })
        
        if results and results[0].get("rate") is not None:
            try:
                strategy_success_rate.labels(strategy_id=strategy_id).set(results[0]["rate"])
            except Exception:
                pass
        
        logger.info(f"Strategy outcome recorded: {strategy_id} -> {'success' if success else 'failure'}")
    
    async def evolve_strategy(self, old_id: str, new_id: str, description: str, reason: str) -> str:
        """
        Создать новую стратегию как эволюцию старой (EVOLVED_FROM).
        """
        try:
            await self.graph.execute_cypher(
                """
                MATCH (old:Strategy {id: $old_id})
                CREATE (new:Strategy {
                    id: $new_id,
                    user_id: $user_id,
                    task_type: old.task_type,
                    description: $description,
                    success_rate: old.success_rate,
                    usage_count: 0,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                CREATE (new)-[:EVOLVED_FROM {reason: $reason}]->(old)
                """,
                {
                    "old_id": old_id,
                    "new_id": new_id,
                    "user_id": self.user_id,
                    "description": description,
                    "reason": reason,
                },
            )
            logger.info(f"Evolved strategy {old_id} -> {new_id} (reason: {reason})")
            return new_id
        except Exception as e:
            logger.error(f"Failed to evolve strategy: {e}")
            raise
    
    async def update_usage(self, strategy_id: str, new_rating: float) -> None:
        """
        Обновить метрику стратегии через взвешенное среднее:
        new_score = (old_score * usage + new_rating) / (usage + 1)
        """
        await self.graph.execute_cypher(
            """
            MATCH (s:Strategy {id: $id})
            WITH s, toFloat(s.success_rate) AS old_score, toInteger(s.usage_count) AS usage
            WITH s, old_score, usage, ((old_score * usage) + $new_rating) / (usage + 1) AS new_score
            SET s.success_rate = new_score,
                s.usage_count = usage + 1,
                s.updated_at = datetime()
            """,
            {"id": strategy_id, "new_rating": float(new_rating)},
        )
    
    async def add_experience(self, context: str, action: str, 
                             outcome: bool, strategy_id: str = None) -> str:
        """Записать опыт (для experience replay)."""
        exp_id = str(uuid.uuid4())
        
        if strategy_id:
            # Связываем опыт со стратегией
            await self.graph.execute_cypher("""
                MATCH (s:Strategy {id: $strategy_id})
                CREATE (e:Experience {
                    id: $exp_id,
                    user_id: $user_id,
                    context: $context,
                    action: $action,
                    outcome: $outcome,
                    created_at: datetime()
                })
                CREATE (e)-[:USED_STRATEGY]->(s)
            """, {
                "exp_id": exp_id,
                "user_id": self.user_id,
                "context": context,
                "action": action,
                "outcome": outcome,
                "strategy_id": strategy_id,
            })
        else:
            await self.graph.execute_cypher("""
                CREATE (e:Experience {
                    id: $exp_id,
                    user_id: $user_id,
                    context: $context,
                    action: $action,
                    outcome: $outcome,
                    created_at: datetime()
                })
            """, {
                "exp_id": exp_id,
                "user_id": self.user_id,
                "context": context,
                "action": action,
                "outcome": outcome,
            })
        
        return exp_id
    
    async def log_experience(
        self,
        task_type: str,
        query: str,
        strategy_used: str,
        outcome: Outcome,
        feedback: str = "",
        context_episode_id: Optional[str] = None,
        context_snapshot: Optional[str] = None,
    ) -> str:
        """
        Записать опыт выполнения задачи.
        
        Это удобный метод-обёртка над add_experience для логирования опыта с контекстом задачи.
        """
        context = f"Task: {task_type}, Query: {query}"
        action = strategy_used or "none"
        outcome_bool = (outcome == Outcome.SUCCESS)
        
        exp_id = await self.add_experience(
            context=context_snapshot or context,
            action=action,
            outcome=outcome_bool,
            strategy_id=None  # Можно улучшить, если будем хранить strategy_id по описанию
        )

        # Привязка опыта к эпизоду (если есть)
        if context_episode_id:
            try:
                await self.graph.execute_cypher(
                    """
                    MATCH (e:Experience {id: $exp_id})
                    MATCH (ep:Episodic {uuid: $ep_id})
                    MERGE (e)-[:APPLIED_IN]->(ep)
                    """,
                    {"exp_id": exp_id, "ep_id": context_episode_id},
                )
            except Exception as e:
                logger.warning(f"Failed to link Experience to Episodic: {e}")
        
        # Если была использована стратегия, обновляем её статистику
        if strategy_used:
            await self._update_strategy_stats(strategy_used, outcome)
        
        return exp_id
    
    async def _update_strategy_stats(self, strategy_desc: str, outcome: Outcome):
        """
        Обновить статистику стратегии (Reinforcement Learning).
        
        Если успех -> confidence растет. Если провал -> падает.
        """
        rating = 1.0 if outcome == Outcome.SUCCESS else 0.0
        if outcome == Outcome.PARTIAL:
            rating = 0.5
        if outcome == Outcome.UNKNOWN:
            rating = 0.5
        
        await self.graph.execute_cypher(
            """
            MERGE (s:Strategy {description: $desc, user_id: $user_id})
            ON CREATE SET 
                s.id = randomUUID(),
                s.created_at = datetime(),
                s.success_rate = 0.5,
                s.usage_count = 0,
                s.task_type = 'general',
                s.updated_at = datetime()
            WITH s
            WITH s, toFloat(s.success_rate) AS old_score, toInteger(s.usage_count) AS usage
            WITH s, ((old_score * usage) + $new_rating) / (usage + 1) AS new_score, usage
            SET s.success_rate = new_score,
                s.usage_count = usage + 1,
                s.updated_at = datetime()
            """,
            {"desc": strategy_desc, "user_id": self.user_id, "new_rating": rating},
        )
    
    async def get_best_strategy(self, task_type: str = None) -> Optional[str]:
        """
        Найти лучшую стратегию для типа задачи.
        
        Returns:
            Описание лучшей стратегии или None если нет подходящих
        """
        if task_type:
            results = await self.graph.execute_cypher("""
                MATCH (s:Strategy {user_id: $user_id})
                WHERE s.task_type = $task_type OR s.task_type = 'general'
                  AND s.confidence > 0.6
                RETURN s.description as desc, s.confidence as conf
                ORDER BY s.confidence DESC
                LIMIT 1
            """, {
                "user_id": self.user_id,
                "task_type": task_type,
            })
        else:
            results = await self.graph.execute_cypher("""
                MATCH (s:Strategy {user_id: $user_id})
                WHERE s.confidence > 0.6
                RETURN s.description as desc, s.confidence as conf
                ORDER BY s.confidence DESC
                LIMIT 1
            """, {
                "user_id": self.user_id,
            })
        
        if results:
            return results[0]["desc"]
        return None
    
    async def get_similar_experiences(self, context: str, 
                                      limit: int = 5) -> List[Dict]:
        """Найти похожий опыт (простой keyword match)."""
        # TODO: заменить на vector similarity когда будет время
        keyword = context.split()[0] if context else ""
        results = await self.graph.execute_cypher("""
            MATCH (e:Experience {user_id: $user_id})
            WHERE toLower(e.context) CONTAINS toLower($keyword)
            RETURN e.id as id,
                   e.context as context,
                   e.action as action,
                   e.outcome as outcome
            ORDER BY e.created_at DESC
            LIMIT $limit
        """, {
            "user_id": self.user_id,
            "keyword": keyword,
            "limit": limit,
        })
        
        experiences = []
        for record in results:
            experiences.append({
                "id": record["id"],
                "context": record["context"],
                "action": record["action"],
                "outcome": record["outcome"],
            })
        
        return experiences

