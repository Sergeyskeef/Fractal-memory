"""
E2E Flow Validator for integration testing.

Tests:
- Full chat flow (message → search → respond → save → learn)
- Memory persistence across restarts
- Learning flow (strategy usage in chat)
"""

import asyncio
import uuid
from typing import List, Optional, Dict, Any

from ..core.base_checker import RuntimeTester
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class E2EFlowValidator(RuntimeTester):
    """Валидация полного цикла работы системы."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="E2EFlowValidator", timeout_seconds=config.runtime_test_timeout_seconds * 2)
        self.config = config
        self.memory = None
        self.agent = None
        self.redis_client = None
        self.neo4j_driver = None
    
    async def _check(self) -> List[Issue]:
        """Выполнить все E2E проверки."""
        issues = []
        
        # Initialize connections
        try:
            await self._initialize_connections()
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
            issues.append(self.create_issue(
                category=Category.INTEGRATION,
                severity=Severity.CRITICAL,
                title="Cannot initialize E2E test environment",
                description=f"Failed to connect to system: {str(e)}",
                location="E2EFlowValidator",
                impact="Cannot test E2E functionality",
                recommendation="Check system initialization and database connections",
            ))
            return issues
        
        try:
            # Test chat flow
            self.logger.info("Testing chat flow...")
            chat_issues = await self.test_chat_flow()
            issues.extend(chat_issues)
            
            # Test memory persistence
            self.logger.info("Testing memory persistence...")
            persistence_issues = await self.test_memory_persistence()
            issues.extend(persistence_issues)
            
            # Test learning flow
            self.logger.info("Testing learning flow...")
            learning_issues = await self.test_learning_flow()
            issues.extend(learning_issues)
        
        finally:
            await self._cleanup_connections()
        
        return issues
    
    async def _initialize_connections(self):
        """Инициализировать подключения к системе."""
        try:
            import sys
            from pathlib import Path
            
            # Add src to path
            src_path = self.config.src_dir
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            # Try to import components
            try:
                from fractal_memory import FractalMemory
                
                # Initialize memory system with config dict
                memory_config = {
                    "neo4j_uri": self.config.neo4j_uri,
                    "neo4j_user": self.config.neo4j_user,
                    "neo4j_password": self.config.neo4j_password,
                    "redis_url": self.config.redis_url,
                    "user_id": "audit_test_user",
                }
                self.memory = FractalMemory(config=memory_config)
                
                await self.memory.initialize()
                self.logger.info("FractalMemory initialized successfully")
            
            except ImportError as e:
                self.logger.warning(f"Cannot import FractalMemory: {e}")
            
            # Try to import agent
            try:
                from src.agent import FractalAgent
                
                if self.memory:
                    self.agent = FractalAgent(memory=self.memory)
                    self.logger.info("FractalAgent initialized successfully with provided memory")
            
            except ImportError as e:
                self.logger.warning(f"Cannot import FractalAgent: {e}")
            
            # Initialize direct connections as fallback
            await self._initialize_direct_connections()
        
        except Exception as e:
            self.logger.error(f"Error initializing connections: {e}")
            raise
    
    async def _initialize_direct_connections(self):
        """Инициализировать прямые подключения к базам данных."""
        try:
            from neo4j import GraphDatabase
            import redis.asyncio as redis
            
            # Connect to Neo4j
            self.neo4j_driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            
            # Connect to Redis
            self.redis_client = await redis.from_url(self.config.redis_url)
            
            self.logger.info("Direct database connections initialized")
        
        except Exception as e:
            self.logger.error(f"Error initializing direct connections: {e}")
            raise
    
    async def _cleanup_connections(self):
        """Закрыть все подключения."""
        try:
            if self.memory:
                await self.memory.close()
            
            if self.redis_client:
                await self.redis_client.close()
            
            if self.neo4j_driver:
                self.neo4j_driver.close()
        
        except Exception as e:
            self.logger.warning(f"Error cleaning up connections: {e}")
    
    async def test_chat_flow(self) -> List[Issue]:
        """
        Тест полного цикла чата: сообщение → поиск → ответ → сохранение → обучение.
        
        Validates: Requirements 1.2, 1.3, 1.4
        """
        issues = []
        
        try:
            if not self.memory:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.HIGH,
                    title="FractalMemory not available for chat flow test",
                    description="Cannot test chat flow without FractalMemory instance",
                    location="E2EFlowValidator.test_chat_flow",
                    impact="Cannot verify full chat flow works correctly",
                    recommendation="Ensure FractalMemory is properly initialized",
                ))
                return issues
            
            # Generate unique test data
            test_user_id = f"test_user_e2e_{uuid.uuid4().hex[:8]}"
            test_message = f"Test message for E2E flow {uuid.uuid4()}"
            
            # Step 1: Store message in memory (simulate receiving)
            self.logger.info(f"Step 1: Storing message for user {test_user_id}")
            message_id = await self.memory.remember(
                content=test_message,
                importance=0.7
            )
            
            if not message_id:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.HIGH,
                    title="Failed to store message in memory",
                    description="remember() returned None or empty",
                    location="Chat flow - Step 1",
                    impact="Cannot store user messages",
                    recommendation="Check FractalMemory.remember() implementation",
                ))
                return issues
            
            # Step 2: Search for the message (simulate retrieval)
            self.logger.info("Step 2: Searching for stored message")
            await asyncio.sleep(0.5)  # Give time for indexing
            
            search_results = await self.memory.search(
                query=test_message[:20],  # Search by first part
                limit=5
            )
            
            if not search_results:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.HIGH,
                    title="Cannot retrieve stored message",
                    description=f"Search returned no results for recently stored message",
                    location="Chat flow - Step 2",
                    impact="Stored messages cannot be retrieved",
                    recommendation="Check search functionality and indexing",
                ))
            else:
                # Verify the message is in results
                found = False
                for result in search_results:
                    result_content = result.content if hasattr(result, 'content') else str(result)
                    if test_message in result_content:
                        found = True
                        break
                
                if not found:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="Stored message not in search results",
                        description=f"Message stored but not found in search results",
                        location="Chat flow - Step 2",
                        impact="Search may not be working correctly",
                        recommendation="Check search relevance and indexing",
                    ))
            
            # Step 3: Verify message is in L0 or L1
            self.logger.info("Step 3: Verifying message in L0/L1")
            if self.redis_client:
                # Check L0
                l0_keys = await self.redis_client.keys(f"memory:{test_user_id}:l0:*")
                # Check L1
                l1_keys = await self.redis_client.keys(f"memory:{test_user_id}:l1:*")
                
                if not l0_keys and not l1_keys:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="Message not found in L0 or L1",
                        description=f"Expected to find message in Redis L0 or L1",
                        location="Chat flow - Step 3",
                        impact="Message may not be stored in short-term memory",
                        recommendation="Check L0/L1 storage logic",
                    ))
                else:
                    self.logger.info(f"Found message in Redis: {len(l0_keys)} L0 keys, {len(l1_keys)} L1 keys")
            
            # Step 4: Trigger consolidation
            self.logger.info("Step 4: Triggering consolidation")
            if hasattr(self.memory, 'consolidate'):
                await self.memory.consolidate()
                await asyncio.sleep(1)
            
            # Step 5: Verify stats are updated
            self.logger.info("Step 5: Verifying stats")
            stats = await self.memory.get_stats()
            
            if not stats:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.MEDIUM,
                    title="Cannot get memory stats",
                    description="get_stats() returned None or empty",
                    location="Chat flow - Step 5",
                    impact="Cannot monitor memory state",
                    recommendation="Check get_stats() implementation",
                ))
            else:
                self.logger.info(f"Memory stats: {stats}")
                
                # Verify stats have reasonable values
                if isinstance(stats, dict):
                    total_items = stats.get('total_items', 0)
                    if total_items == 0:
                        issues.append(self.create_issue(
                            category=Category.INTEGRATION,
                            severity=Severity.LOW,
                            title="Memory stats show zero items",
                            description="Stats report 0 total items despite storing data",
                            location="Chat flow - Step 5",
                            impact="Stats may not be accurate",
                            recommendation="Check stats calculation logic",
                        ))
            
            # Step 6: Test agent integration (if available)
            if self.agent:
                self.logger.info("Step 6: Testing agent integration")
                try:
                    # Try to get a response from agent
                    response = await self.agent.process_message(
                        message="What do you remember?",
                        user_id=test_user_id
                    )
                    
                    if not response:
                        issues.append(self.create_issue(
                            category=Category.INTEGRATION,
                            severity=Severity.MEDIUM,
                            title="Agent returned no response",
                            description="Agent.process_message() returned None or empty",
                            location="Chat flow - Step 6",
                            impact="Agent cannot generate responses",
                            recommendation="Check agent implementation",
                        ))
                
                except Exception as e:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="Agent integration failed",
                        description=f"Exception: {str(e)}",
                        location="Chat flow - Step 6",
                        impact="Agent cannot process messages",
                        recommendation="Check agent integration with memory",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error in chat flow test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.INTEGRATION,
                severity=Severity.HIGH,
                title="Chat flow test failed",
                description=f"Exception: {str(e)}",
                location="E2EFlowValidator.test_chat_flow",
                impact="Cannot verify chat flow works correctly",
                recommendation="Fix the error in chat flow logic",
            ))
        
        return issues
    
    async def test_memory_persistence(self) -> List[Issue]:
        """
        Тест персистентности памяти.
        
        Проверяет что данные сохраняются и восстанавливаются после перезапуска.
        Validates: Requirements 1.2, 1.3
        """
        issues = []
        
        try:
            if not self.memory or not self.neo4j_driver:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.HIGH,
                    title="Cannot test memory persistence",
                    description="Need both FractalMemory and Neo4j connection",
                    location="E2EFlowValidator.test_memory_persistence",
                    impact="Cannot verify data persists correctly",
                    recommendation="Ensure all connections are initialized",
                ))
                return issues
            
            # Generate unique test data
            test_user_id = f"test_user_persist_{uuid.uuid4().hex[:8]}"
            test_content = f"Persistent test data {uuid.uuid4()}"
            
            # Store data with high importance (should go to L2)
            self.logger.info("Storing high-importance data")
            await self.memory.remember(
                content=test_content,
                importance=0.95
            )
            
            # Trigger consolidation to move to L2
            if hasattr(self.memory, 'consolidate'):
                await self.memory.consolidate()
                await asyncio.sleep(2)
            
            # Check if data is in Neo4j (L2)
            self.logger.info("Checking if data persisted to Neo4j")
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (e:Episodic)
                    WHERE e.content CONTAINS $content_part
                    RETURN count(e) as count
                """, content_part=test_content[:20])
                
                record = result.single()
                count = record["count"] if record else 0
                
                if count == 0:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.HIGH,
                        title="High-importance data not persisted to Neo4j",
                        description=f"Data with importance 0.95 not found in L2 after consolidation",
                        location="Memory persistence test",
                        impact="Important data may be lost",
                        recommendation="Check L1→L2 consolidation logic",
                    ))
                else:
                    self.logger.info(f"Found {count} matching Episodic nodes in Neo4j")
            
            # Simulate restart by closing and reopening memory
            self.logger.info("Simulating restart")
            await self.memory.close()
            
            # Reinitialize
            from fractal_memory import FractalMemory
            memory_config = {
                "neo4j_uri": self.config.neo4j_uri,
                "neo4j_user": self.config.neo4j_user,
                "neo4j_password": self.config.neo4j_password,
                "redis_url": self.config.redis_url,
                "user_id": "audit_test_user",
            }
            self.memory = FractalMemory(config=memory_config)
            await self.memory.initialize()
            
            # Try to search for the data
            self.logger.info("Searching for data after restart")
            search_results = await self.memory.search(
                query=test_content[:20],
                limit=5
            )
            
            if not search_results:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.HIGH,
                    title="Data not retrievable after restart",
                    description="Persisted data cannot be found after system restart",
                    location="Memory persistence test",
                    impact="Data may be lost on restart",
                    recommendation="Check data persistence and search after initialization",
                ))
            else:
                # Verify the content is in results
                found = False
                for result in search_results:
                    result_content = result.content if hasattr(result, 'content') else str(result)
                    if test_content in result_content:
                        found = True
                        break
                
                if not found:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="Persisted data not in search results after restart",
                        description="Data exists in Neo4j but not returned by search",
                        location="Memory persistence test",
                        impact="Search may not work correctly after restart",
                        recommendation="Check search initialization and indexing",
                    ))
                else:
                    self.logger.info("Successfully retrieved persisted data after restart")
        
        except Exception as e:
            self.logger.error(f"Error in persistence test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.INTEGRATION,
                severity=Severity.HIGH,
                title="Memory persistence test failed",
                description=f"Exception: {str(e)}",
                location="E2EFlowValidator.test_memory_persistence",
                impact="Cannot verify data persists correctly",
                recommendation="Fix the error in persistence logic",
            ))
        
        return issues
    
    async def test_learning_flow(self) -> List[Issue]:
        """
        Тест потока обучения.
        
        Проверяет что стратегии используются в чате.
        Validates: Requirements 1.4, 9.5
        """
        issues = []
        
        try:
            if not self.neo4j_driver:
                issues.append(self.create_issue(
                    category=Category.INTEGRATION,
                    severity=Severity.MEDIUM,
                    title="Cannot test learning flow without Neo4j",
                    description="Need Neo4j connection to check strategies",
                    location="E2EFlowValidator.test_learning_flow",
                    impact="Cannot verify learning functionality",
                    recommendation="Ensure Neo4j connection is initialized",
                ))
                return issues
            
            # Check if Strategy nodes exist
            self.logger.info("Checking for Strategy nodes")
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (s:Strategy)
                    RETURN count(s) as count
                """)
                
                record = result.single()
                strategy_count = record["count"] if record else 0
                
                if strategy_count == 0:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="No Strategy nodes found",
                        description="Expected to find Strategy nodes for learning",
                        location="Learning flow test",
                        impact="Learning system may not be working",
                        recommendation="Check ReasoningBank integration and strategy creation",
                    ))
                else:
                    self.logger.info(f"Found {strategy_count} Strategy nodes")
                    
                    # Check if strategies have required fields
                    result = session.run("""
                        MATCH (s:Strategy)
                        RETURN s.task_type as task_type, 
                               s.description as strategy,
                               s.success_rate as success_rate
                        LIMIT 5
                    """)
                    
                    for record in result:
                        task_type = record.get("task_type")
                        strategy = record.get("strategy")
                        success_rate = record.get("success_rate")
                        
                        if not task_type:
                            issues.append(self.create_issue(
                                category=Category.INTEGRATION,
                                severity=Severity.MEDIUM,
                                title="Strategy missing task_type",
                                description="Strategy node missing required task_type field",
                                location="Learning flow test",
                                impact="Cannot categorize strategies",
                                recommendation="Ensure all strategies have task_type",
                            ))
                        
                        if not strategy:
                            issues.append(self.create_issue(
                                category=Category.INTEGRATION,
                                severity=Severity.MEDIUM,
                                title="Strategy missing strategy content",
                                description="Strategy node missing required strategy field",
                                location="Learning flow test",
                                impact="Strategy has no content",
                                recommendation="Ensure all strategies have strategy content",
                            ))
                        
                        if success_rate is None:
                            issues.append(self.create_issue(
                                category=Category.INTEGRATION,
                                severity=Severity.LOW,
                                title="Strategy missing success_rate",
                                description="Strategy node missing success_rate field",
                                location="Learning flow test",
                                impact="Cannot track strategy effectiveness",
                                recommendation="Initialize success_rate for all strategies",
                            ))
                
                # Check for Experience nodes
                result = session.run("""
                    MATCH (e:Experience)
                    RETURN count(e) as count
                """)
                
                record = result.single()
                experience_count = record["count"] if record else 0
                
                if experience_count == 0:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.LOW,
                        title="No Experience nodes found",
                        description="Expected to find Experience nodes for learning history",
                        location="Learning flow test",
                        impact="No learning history recorded",
                        recommendation="Check experience logging in ReasoningBank",
                    ))
                else:
                    self.logger.info(f"Found {experience_count} Experience nodes")
                
                # Check for USED_STRATEGY relationships
                result = session.run("""
                    MATCH (e:Experience)-[r:USED_STRATEGY]->(s:Strategy)
                    RETURN count(r) as count
                """)
                
                record = result.single()
                used_count = record["count"] if record else 0
                
                if strategy_count > 0 and experience_count > 0 and used_count == 0:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="No USED_STRATEGY relationships found",
                        description="Strategies and experiences exist but not linked",
                        location="Learning flow test",
                        impact="Cannot track which strategies were used",
                        recommendation="Check relationship creation in ReasoningBank",
                    ))
                else:
                    self.logger.info(f"Found {used_count} USED_STRATEGY relationships")
            
            # Test agent integration with strategies (if agent available)
            if self.agent:
                self.logger.info("Testing agent strategy usage")
                try:
                    # Check if agent has reasoning_bank
                    if hasattr(self.agent, 'reasoning_bank'):
                        # Try to get strategies
                        strategies = await self.agent.reasoning_bank.get_strategies(
                            task_type="general",
                            limit=5
                        )
                        
                        if not strategies:
                            issues.append(self.create_issue(
                                category=Category.INTEGRATION,
                                severity=Severity.LOW,
                                title="Agent cannot retrieve strategies",
                                description="ReasoningBank.get_strategies() returned no results",
                                location="Learning flow test",
                                impact="Agent cannot use learned strategies",
                                recommendation="Check strategy retrieval logic",
                            ))
                        else:
                            self.logger.info(f"Agent retrieved {len(strategies)} strategies")
                    else:
                        issues.append(self.create_issue(
                            category=Category.INTEGRATION,
                            severity=Severity.MEDIUM,
                            title="Agent missing reasoning_bank",
                            description="FractalAgent does not have reasoning_bank attribute",
                            location="Learning flow test",
                            impact="Agent cannot use learning functionality",
                            recommendation="Integrate ReasoningBank with FractalAgent",
                        ))
                
                except Exception as e:
                    issues.append(self.create_issue(
                        category=Category.INTEGRATION,
                        severity=Severity.MEDIUM,
                        title="Error testing agent strategy usage",
                        description=f"Exception: {str(e)}",
                        location="Learning flow test",
                        impact="Cannot verify agent uses strategies",
                        recommendation="Check agent-ReasoningBank integration",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error in learning flow test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.INTEGRATION,
                severity=Severity.HIGH,
                title="Learning flow test failed",
                description=f"Exception: {str(e)}",
                location="E2EFlowValidator.test_learning_flow",
                impact="Cannot verify learning flow works correctly",
                recommendation="Fix the error in learning flow logic",
            ))
        
        return issues
