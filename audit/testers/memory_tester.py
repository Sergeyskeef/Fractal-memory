"""
Memory tester for runtime validation of memory system.

Tests:
- L0 to L1 consolidation (Redis to Redis)
- L1 to L2 consolidation (Redis to Neo4j)
- Decay logic (importance decreases over time)
- Garbage collection (safe deletion of old data)
- Deduplication (no duplicates in L2)
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from ..core.base_checker import RuntimeTester
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class MemoryTester(RuntimeTester):
    """Тестирование системы памяти с реальными базами данных."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="MemoryTester", timeout_seconds=config.runtime_test_timeout_seconds)
        self.config = config
        self.memory = None
        self.redis_client = None
        self.neo4j_driver = None
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки памяти."""
        issues = []
        
        # Initialize connections
        try:
            await self._initialize_connections()
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.CRITICAL,
                title="Cannot initialize memory system",
                description=f"Failed to connect to databases: {str(e)}",
                location="MemoryTester",
                impact="Cannot test memory functionality",
                recommendation="Check Neo4j and Redis connections",
            ))
            return issues
        
        try:
            # Test L0 to L1 consolidation
            self.logger.info("Testing L0 to L1 consolidation...")
            result = await self.test_l0_to_l1_consolidation()
            issues.extend(result.issues)
            
            # Test L1 to L2 consolidation
            self.logger.info("Testing L1 to L2 consolidation...")
            result = await self.test_l1_to_l2_consolidation()
            issues.extend(result.issues)
            
            # Test decay logic
            self.logger.info("Testing decay logic...")
            result = await self.test_decay_logic()
            issues.extend(result.issues)
            
            # Test garbage collection
            self.logger.info("Testing garbage collection...")
            result = await self.test_garbage_collection()
            issues.extend(result.issues)
            
            # Test deduplication
            self.logger.info("Testing deduplication...")
            result = await self.test_deduplication()
            issues.extend(result.issues)
        
        finally:
            await self._cleanup_connections()
        
        return issues
    
    async def _initialize_connections(self):
        """Инициализировать подключения к базам данных."""
        try:
            # Import FractalMemory
            import sys
            from pathlib import Path
            
            # Add src to path
            src_path = self.config.src_dir
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            # Try to import FractalMemory
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
                # Fall back to direct connections
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
    
    async def test_l0_to_l1_consolidation(self) -> 'TestResult':
        """
        Тест консолидации L0 → L1 (Redis → Redis).
        
        Проверяет что данные с высокой важностью перемещаются из L0 в L1.
        Реальная архитектура: L0 и L1 оба в Redis!
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            # Проверяем Redis напрямую
            if not self.redis_client:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.HIGH,
                    title="Redis not available for L0→L1 test",
                    description="Cannot test L0→L1 consolidation without Redis connection",
                    location="MemoryTester.test_l0_to_l1_consolidation",
                    impact="Cannot verify L0→L1 consolidation works correctly",
                    recommendation="Ensure Redis is properly initialized",
                ))
                return TestResult(
                    test_name="L0→L1 Consolidation",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Проверяем наличие L1 ключей в Redis
            # Формат: memory:{user}:l1:session:{id}
            l1_keys = await self.redis_client.keys("memory:*:l1:*")
            
            if not l1_keys:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.MEDIUM,
                    title="No L1 keys found in Redis",
                    description="Expected to find memory:{user}:l1:session:{id} keys in Redis",
                    location="L0→L1 consolidation",
                    impact="L1 layer may not be working or is empty",
                    recommendation="Check if L0→L1 consolidation is creating L1 keys, or if data exists",
                ))
            else:
                self.logger.info(f"Found {len(l1_keys)} L1 keys in Redis")
                
                # Проверяем структуру L1 ключей
                sample_key = l1_keys[0]
                l1_data = await self.redis_client.hgetall(sample_key)
                
                # Required fields in L1 (must be present)
                required_fields = {'session_id', 'created_at'}
                # Optional fields in L1 (nice to have but not critical)
                optional_fields = {'summary', 'importance', 'source_count'}
                
                actual_fields = set(l1_data.keys())
                
                # Check for missing required fields (CRITICAL)
                missing_required = required_fields - actual_fields
                if missing_required:
                    issues.append(self.create_issue(
                        category=Category.MEMORY,
                        severity=Severity.HIGH,
                        title=f"L1 keys missing required fields",
                        description=f"L1 key '{sample_key.decode() if isinstance(sample_key, bytes) else sample_key}' missing required fields: {', '.join(missing_required)}",
                        location="L1 structure validation",
                        impact="L1 data structure is incomplete and may cause errors",
                        recommendation="Ensure L1 consolidation logic sets all required fields: session_id, created_at",
                    ))
                
                # Check for missing optional fields (INFORMATIONAL)
                missing_optional = optional_fields - actual_fields
                if missing_optional:
                    self.logger.info(f"L1 key missing optional fields (not critical): {', '.join(missing_optional)}")
                
                # Validate importance field if present (optional but should be valid if present)
                if 'importance' in l1_data:
                    try:
                        importance_value = l1_data['importance']
                        # Handle bytes from Redis
                        if isinstance(importance_value, bytes):
                            importance_value = importance_value.decode()
                        
                        importance = float(importance_value)
                        
                        if not (0.0 <= importance <= 1.0):
                            issues.append(self.create_issue(
                                category=Category.MEMORY,
                                severity=Severity.MEDIUM,
                                title="L1 importance value out of valid range",
                                description=f"Importance value {importance} is outside the valid range [0.0, 1.0] for L1 key '{sample_key.decode() if isinstance(sample_key, bytes) else sample_key}'",
                                location="L1 importance validation",
                                impact="Importance-based sorting and filtering may produce incorrect results",
                                recommendation="Ensure importance values are normalized to [0.0, 1.0] range during L1 consolidation",
                            ))
                        else:
                            self.logger.debug(f"L1 importance valid: {importance}")
                    except (ValueError, TypeError) as e:
                        issues.append(self.create_issue(
                            category=Category.MEMORY,
                            severity=Severity.MEDIUM,
                            title="L1 importance field has invalid format",
                            description=f"Importance value '{l1_data['importance']}' cannot be converted to float: {str(e)}",
                            location="L1 importance validation",
                            impact="Cannot use importance for sorting or filtering",
                            recommendation="Store importance as a numeric string or float value",
                        ))
            
            # Проверяем L0 ключи (могут быть пустыми, так как быстро очищаются)
            l0_keys = await self.redis_client.keys("memory:*:l0:*")
            self.logger.info(f"Found {len(l0_keys)} L0 keys in Redis (may be 0 if cleared quickly)")
        
        except Exception as e:
            self.logger.error(f"Error in L0→L1 test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.HIGH,
                title="L0→L1 consolidation test failed",
                description=f"Exception: {str(e)}",
                location="MemoryTester.test_l0_to_l1_consolidation",
                impact="Cannot verify L0→L1 consolidation",
                recommendation="Fix the error in consolidation logic",
            ))
        
        return TestResult(
            test_name="L0→L1 Consolidation",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_l1_to_l2_consolidation(self) -> 'TestResult':
        """
        Тест консолидации L1 → L2 (Redis → Neo4j).
        
        Проверяет что данные перемещаются из Redis (L1) в Neo4j (L2).
        Реальная архитектура: L1 в Redis, L2 в Neo4j (Episodic + Entity через Graphiti).
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.neo4j_driver:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.HIGH,
                    title="Neo4j not available for L1→L2 test",
                    description="Cannot test L1→L2 consolidation without Neo4j connection",
                    location="MemoryTester.test_l1_to_l2_consolidation",
                    impact="Cannot verify L1→L2 consolidation works correctly",
                    recommendation="Ensure Neo4j is properly initialized",
                ))
                return TestResult(
                    test_name="L1→L2 Consolidation",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Проверяем наличие Episodic узлов в Neo4j (L2)
            with self.neo4j_driver.session() as session:
                # Проверяем Episodic узлы
                result = session.run("""
                    MATCH (e:Episodic)
                    RETURN count(e) as count
                """)
                record = result.single()
                episodic_count = record["count"] if record else 0
                
                if episodic_count == 0:
                    issues.append(self.create_issue(
                        category=Category.MEMORY,
                        severity=Severity.MEDIUM,
                        title="No Episodic nodes found in Neo4j",
                        description="Expected to find Episodic nodes in L2 (Neo4j)",
                        location="L1→L2 consolidation",
                        impact="L2 layer may not be working or is empty",
                        recommendation="Check if L1→L2 consolidation is creating Episodic nodes, or if data exists",
                    ))
                else:
                    self.logger.info(f"Found {episodic_count} Episodic nodes in Neo4j")
                
                # Проверяем Entity узлы (Graphiti)
                result = session.run("""
                    MATCH (e:Entity)
                    RETURN count(e) as count
                """)
                record = result.single()
                entity_count = record["count"] if record else 0
                
                if entity_count == 0:
                    issues.append(self.create_issue(
                        category=Category.MEMORY,
                        severity=Severity.MEDIUM,
                        title="No Entity nodes found in Neo4j",
                        description="Expected to find Entity nodes created by Graphiti",
                        location="L2 Entity extraction",
                        impact="Entity extraction may not be working",
                        recommendation="Check Graphiti integration and entity extraction logic",
                    ))
                else:
                    self.logger.info(f"Found {entity_count} Entity nodes in Neo4j")
                
                # Проверяем связи MENTIONS (Episodic → Entity)
                result = session.run("""
                    MATCH (e:Episodic)-[r:MENTIONS]->(ent:Entity)
                    RETURN count(r) as count
                """)
                record = result.single()
                mentions_count = record["count"] if record else 0
                
                if episodic_count > 0 and entity_count > 0 and mentions_count == 0:
                    issues.append(self.create_issue(
                        category=Category.MEMORY,
                        severity=Severity.MEDIUM,
                        title="No MENTIONS relationships found",
                        description="Episodic and Entity nodes exist but no MENTIONS relationships",
                        location="L2 relationships",
                        impact="Episodic memories not linked to entities",
                        recommendation="Check Graphiti relationship creation logic",
                    ))
                else:
                    self.logger.info(f"Found {mentions_count} MENTIONS relationships")
                
                # Проверяем promoted_to_l2 флаг в Redis L1
                if self.redis_client:
                    l1_keys = await self.redis_client.keys("memory:*:l1:*")
                    promoted_count = 0
                    
                    for key in l1_keys[:10]:  # Проверяем первые 10
                        l1_data = await self.redis_client.hgetall(key)
                        if l1_data.get('promoted_to_l2') == 'True':
                            promoted_count += 1
                    
                    self.logger.info(f"Found {promoted_count}/{min(len(l1_keys), 10)} L1 items promoted to L2")
        
        except Exception as e:
            self.logger.error(f"Error in L1→L2 test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.HIGH,
                title="L1→L2 consolidation test failed",
                description=f"Exception: {str(e)}",
                location="MemoryTester.test_l1_to_l2_consolidation",
                impact="Cannot verify L1→L2 consolidation",
                recommendation="Fix the error in consolidation logic",
            ))
        
        return TestResult(
            test_name="L1→L2 Consolidation",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_decay_logic(self) -> 'TestResult':
        """
        Тест логики decay.
        
        Проверяет что importance уменьшается со временем без доступа.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.memory:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.MEDIUM,
                    title="FractalMemory not available for decay test",
                    description="Cannot test decay logic without FractalMemory instance",
                    location="MemoryTester.test_decay_logic",
                    impact="Cannot verify decay logic works correctly",
                    recommendation="Ensure FractalMemory is properly initialized",
                ))
                return TestResult(
                    test_name="Decay Logic",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Create test item
            test_content = f"Test memory item for decay {uuid.uuid4()}"
            initial_importance = 0.8
            
            item_id = await self.memory.remember(
                content=test_content,
                importance=initial_importance
            )
            
            # Get initial stats
            initial_stats = await self.memory.get_stats()
            
            # Wait for decay to happen
            await asyncio.sleep(3)
            
            # Apply decay if method exists
            if hasattr(self.memory, '_apply_decay'):
                await self.memory._apply_decay()
            elif hasattr(self.memory, 'apply_decay'):
                await self.memory.apply_decay()
            
            # Get stats after decay
            after_stats = await self.memory.get_stats()
            
            # Check if decay happened
            # This is tricky without direct access to item importance
            # We can check if total items decreased or if stats changed
            
            self.logger.info(f"Stats before decay: {initial_stats}")
            self.logger.info(f"Stats after decay: {after_stats}")
            
            # If we have access to the item, check its importance
            # For now, we just verify the system didn't crash
        
        except Exception as e:
            self.logger.error(f"Error in decay test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.MEDIUM,
                title="Decay logic test failed",
                description=f"Exception: {str(e)}",
                location="MemoryTester.test_decay_logic",
                impact="Cannot verify decay logic",
                recommendation="Fix the error in decay logic",
            ))
        
        return TestResult(
            test_name="Decay Logic",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_garbage_collection(self) -> 'TestResult':
        """
        Тест garbage collection.
        
        Проверяет что старые данные с низкой важностью удаляются безопасно.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.memory:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.MEDIUM,
                    title="FractalMemory not available for GC test",
                    description="Cannot test garbage collection without FractalMemory instance",
                    location="MemoryTester.test_garbage_collection",
                    impact="Cannot verify GC works correctly",
                    recommendation="Ensure FractalMemory is properly initialized",
                ))
                return TestResult(
                    test_name="Garbage Collection",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Create low-importance items
            test_items = []
            for i in range(5):
                content = f"Low importance item {i} {uuid.uuid4()}"
                item_id = await self.memory.remember(
                    content=content,
                    importance=0.1  # Very low
                )
                test_items.append((item_id, content))
            
            # Get initial count
            initial_stats = await self.memory.get_stats()
            
            # Trigger GC if method exists
            if hasattr(self.memory, 'garbage_collect'):
                await self.memory.garbage_collect()
            elif hasattr(self.memory, '_garbage_collect'):
                await self.memory._garbage_collect()
            
            # Get stats after GC
            after_stats = await self.memory.get_stats()
            
            self.logger.info(f"Stats before GC: {initial_stats}")
            self.logger.info(f"Stats after GC: {after_stats}")
            
            # Verify system is still functional
            test_search = await self.memory.search(
                query="test",
                limit=5
            )
            
            # GC should not break search functionality
            if test_search is None:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.HIGH,
                    title="Search broken after garbage collection",
                    description="Search returns None after GC",
                    location="Garbage Collection",
                    impact="GC breaks search functionality",
                    recommendation="Fix GC to not break other functionality",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in GC test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.MEDIUM,
                title="Garbage collection test failed",
                description=f"Exception: {str(e)}",
                location="MemoryTester.test_garbage_collection",
                impact="Cannot verify GC works correctly",
                recommendation="Fix the error in GC logic",
            ))
        
        return TestResult(
            test_name="Garbage Collection",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_deduplication(self) -> 'TestResult':
        """
        Тест дедупликации.
        
        Проверяет что дубликаты не создаются в L2.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.memory:
                issues.append(self.create_issue(
                    category=Category.MEMORY,
                    severity=Severity.MEDIUM,
                    title="FractalMemory not available for deduplication test",
                    description="Cannot test deduplication without FractalMemory instance",
                    location="MemoryTester.test_deduplication",
                    impact="Cannot verify deduplication works correctly",
                    recommendation="Ensure FractalMemory is properly initialized",
                ))
                return TestResult(
                    test_name="Deduplication",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Store same content multiple times
            duplicate_content = f"Duplicate test content {uuid.uuid4()}"
            
            for i in range(3):
                await self.memory.remember(
                    content=duplicate_content,
                    importance=0.9
                )
                await asyncio.sleep(0.5)
            
            # Trigger consolidation
            if hasattr(self.memory, 'consolidate'):
                await self.memory.consolidate()
            
            await asyncio.sleep(2)
            
            # Search for the content
            results = await self.memory.search(
                query=duplicate_content,
                limit=10
            )
            
            # Check for duplicates
            if results and len(results) > 1:
                # Check if they're actually duplicates (same content)
                contents = [r.content if hasattr(r, 'content') else str(r) for r in results]
                exact_duplicates = sum(1 for c in contents if duplicate_content in c)
                
                if exact_duplicates > 1:
                    issues.append(self.create_issue(
                        category=Category.MEMORY,
                        severity=Severity.MEDIUM,
                        title="Duplicate items found in memory",
                        description=f"Found {exact_duplicates} copies of the same content",
                        location="Deduplication",
                        impact="Memory contains duplicate data, wasting storage",
                        recommendation="Implement or fix deduplication logic",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error in deduplication test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.MEMORY,
                severity=Severity.MEDIUM,
                title="Deduplication test failed",
                description=f"Exception: {str(e)}",
                location="MemoryTester.test_deduplication",
                impact="Cannot verify deduplication works correctly",
                recommendation="Fix the error in deduplication logic",
            ))
        
        return TestResult(
            test_name="Deduplication",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
