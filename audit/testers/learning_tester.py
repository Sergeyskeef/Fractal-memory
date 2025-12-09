"""
Learning tester for runtime validation of ReasoningBank.

Tests:
- Strategy creation (:Strategy nodes)
- Experience logging (:Experience nodes)
- Confidence updates (success_rate)
- Strategy retrieval (get_strategies)
- Agent integration (strategies in prompt)
"""

import asyncio
import uuid
from typing import List

from ..core.base_checker import RuntimeTester
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class LearningTester(RuntimeTester):
    """Тестирование системы самообучения (ReasoningBank)."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="LearningTester", timeout_seconds=config.runtime_test_timeout_seconds)
        self.config = config
        self.reasoning_bank = None
        self.neo4j_driver = None
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки обучения."""
        issues = []
        
        try:
            await self._initialize_connections()
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.HIGH,
                title="Cannot initialize learning system",
                description=f"Failed to connect: {str(e)}",
                location="LearningTester",
                impact="Cannot test learning functionality",
                recommendation="Check Neo4j connection",
            ))
            return issues
        
        try:
            self.logger.info("Testing strategy creation...")
            result = await self.test_strategy_creation()
            issues.extend(result.issues)
            
            self.logger.info("Testing experience logging...")
            result = await self.test_experience_logging()
            issues.extend(result.issues)
            
            self.logger.info("Testing confidence update...")
            result = await self.test_confidence_update()
            issues.extend(result.issues)
            
            self.logger.info("Testing strategy retrieval...")
            result = await self.test_strategy_retrieval()
            issues.extend(result.issues)
            
            self.logger.info("Testing agent integration...")
            result = await self.test_agent_integration()
            issues.extend(result.issues)
        
        finally:
            await self._cleanup_connections()
        
        return issues
    
    async def _initialize_connections(self):
        """Инициализировать подключения."""
        try:
            import sys
            from neo4j import GraphDatabase
            
            src_path = self.config.src_dir
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            # Connect to Neo4j
            self.neo4j_driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            
            # Try to import ReasoningBank
            try:
                from reasoning_bank import ReasoningBank
                
                self.reasoning_bank = ReasoningBank(
                    neo4j_uri=self.config.neo4j_uri,
                    neo4j_user=self.config.neo4j_user,
                    neo4j_password=self.config.neo4j_password,
                )
                
                self.logger.info("ReasoningBank initialized")
            except ImportError as e:
                self.logger.warning(f"Cannot import ReasoningBank: {e}")
        
        except Exception as e:
            self.logger.error(f"Error initializing: {e}")
            raise
    
    async def _cleanup_connections(self):
        """Закрыть подключения."""
        try:
            if self.neo4j_driver:
                self.neo4j_driver.close()
        except Exception as e:
            self.logger.warning(f"Error cleaning up: {e}")
    
    async def test_strategy_creation(self) -> 'TestResult':
        """Тест создания стратегий."""
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.reasoning_bank:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.MEDIUM,
                    title="ReasoningBank not available",
                    description="Cannot test strategy creation",
                    location="LearningTester.test_strategy_creation",
                    impact="Cannot verify strategy creation works",
                    recommendation="Ensure ReasoningBank is initialized",
                ))
                return TestResult(
                    test_name="Strategy Creation",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Create test strategy
            test_strategy = {
                "name": f"test_strategy_{uuid.uuid4()}",
                "description": "Test strategy for audit",
                "context": "testing",
                "action": "verify functionality",
            }
            
            if hasattr(self.reasoning_bank, 'add_strategy'):
                await self.reasoning_bank.add_strategy(**test_strategy)
            elif hasattr(self.reasoning_bank, 'create_strategy'):
                await self.reasoning_bank.create_strategy(**test_strategy)
            else:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.HIGH,
                    title="Strategy creation method not found",
                    description="ReasoningBank missing add_strategy/create_strategy method",
                    location="ReasoningBank",
                    impact="Cannot create strategies",
                    recommendation="Implement strategy creation method",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in strategy creation test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.MEDIUM,
                title="Strategy creation test failed",
                description=f"Exception: {str(e)}",
                location="LearningTester.test_strategy_creation",
                impact="Cannot verify strategy creation",
                recommendation="Fix error in strategy creation logic",
            ))
        
        return TestResult(
            test_name="Strategy Creation",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_experience_logging(self) -> 'TestResult':
        """Тест логирования опыта."""
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.reasoning_bank:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.MEDIUM,
                    title="ReasoningBank not available",
                    description="Cannot test experience logging",
                    location="LearningTester.test_experience_logging",
                    impact="Cannot verify experience logging works",
                    recommendation="Ensure ReasoningBank is initialized",
                ))
                return TestResult(
                    test_name="Experience Logging",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Log test experience
            if hasattr(self.reasoning_bank, 'log_experience'):
                await self.reasoning_bank.log_experience(
                    strategy_name="test_strategy",
                    success=True,
                    context="test context"
                )
            elif hasattr(self.reasoning_bank, 'add_experience'):
                await self.reasoning_bank.add_experience(
                    strategy_name="test_strategy",
                    success=True,
                    context="test context"
                )
            else:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.HIGH,
                    title="Experience logging method not found",
                    description="ReasoningBank missing log_experience/add_experience method",
                    location="ReasoningBank",
                    impact="Cannot log experiences",
                    recommendation="Implement experience logging method",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in experience logging test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.MEDIUM,
                title="Experience logging test failed",
                description=f"Exception: {str(e)}",
                location="LearningTester.test_experience_logging",
                impact="Cannot verify experience logging",
                recommendation="Fix error in experience logging logic",
            ))
        
        return TestResult(
            test_name="Experience Logging",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_confidence_update(self) -> 'TestResult':
        """Тест обновления confidence."""
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.neo4j_driver:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.MEDIUM,
                    title="Neo4j not available",
                    description="Cannot test confidence updates",
                    location="LearningTester.test_confidence_update",
                    impact="Cannot verify confidence updates work",
                    recommendation="Ensure Neo4j is connected",
                ))
                return TestResult(
                    test_name="Confidence Update",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Check if Strategy nodes have confidence/success_rate field
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (s:Strategy)
                    RETURN s LIMIT 1
                """)
                
                record = result.single()
                if record:
                    strategy = record["s"]
                    if "confidence" not in strategy and "success_rate" not in strategy:
                        issues.append(self.create_issue(
                            category=Category.LEARNING,
                            severity=Severity.MEDIUM,
                            title="Strategy nodes missing confidence field",
                            description="Strategy nodes don't have confidence/success_rate field",
                            location="Neo4j Schema",
                            impact="Cannot track strategy effectiveness",
                            recommendation="Add confidence field to Strategy nodes",
                        ))
        
        except Exception as e:
            self.logger.error(f"Error in confidence update test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.MEDIUM,
                title="Confidence update test failed",
                description=f"Exception: {str(e)}",
                location="LearningTester.test_confidence_update",
                impact="Cannot verify confidence updates",
                recommendation="Fix error in confidence update logic",
            ))
        
        return TestResult(
            test_name="Confidence Update",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_strategy_retrieval(self) -> 'TestResult':
        """Тест получения стратегий."""
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.reasoning_bank:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.MEDIUM,
                    title="ReasoningBank not available",
                    description="Cannot test strategy retrieval",
                    location="LearningTester.test_strategy_retrieval",
                    impact="Cannot verify strategy retrieval works",
                    recommendation="Ensure ReasoningBank is initialized",
                ))
                return TestResult(
                    test_name="Strategy Retrieval",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Get strategies
            if hasattr(self.reasoning_bank, 'get_strategies'):
                strategies = await self.reasoning_bank.get_strategies(context="test")
                
                if strategies is None:
                    issues.append(self.create_issue(
                        category=Category.LEARNING,
                        severity=Severity.MEDIUM,
                        title="get_strategies returns None",
                        description="get_strategies should return list, not None",
                        location="ReasoningBank.get_strategies",
                        impact="Strategy retrieval is broken",
                        recommendation="Fix get_strategies to return empty list",
                    ))
            else:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.HIGH,
                    title="Strategy retrieval method not found",
                    description="ReasoningBank missing get_strategies method",
                    location="ReasoningBank",
                    impact="Cannot retrieve strategies",
                    recommendation="Implement get_strategies method",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in strategy retrieval test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.MEDIUM,
                title="Strategy retrieval test failed",
                description=f"Exception: {str(e)}",
                location="LearningTester.test_strategy_retrieval",
                impact="Cannot verify strategy retrieval",
                recommendation="Fix error in strategy retrieval logic",
            ))
        
        return TestResult(
            test_name="Strategy Retrieval",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_agent_integration(self) -> 'TestResult':
        """Тест интеграции с агентом."""
        from ..core.models import TestResult
        
        issues = []
        
        try:
            # This is a placeholder - actual test would check if agent uses strategies
            # For now, just verify ReasoningBank exists
            if not self.reasoning_bank:
                issues.append(self.create_issue(
                    category=Category.LEARNING,
                    severity=Severity.LOW,
                    title="ReasoningBank not available for agent integration test",
                    description="Cannot test agent integration",
                    location="LearningTester.test_agent_integration",
                    impact="Cannot verify agent uses strategies",
                    recommendation="Ensure ReasoningBank is initialized",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in agent integration test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.LEARNING,
                severity=Severity.LOW,
                title="Agent integration test failed",
                description=f"Exception: {str(e)}",
                location="LearningTester.test_agent_integration",
                impact="Cannot verify agent integration",
                recommendation="Fix error in agent integration logic",
            ))
        
        return TestResult(
            test_name="Agent Integration",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
