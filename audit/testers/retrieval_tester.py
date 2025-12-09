"""
Retrieval tester for runtime validation of search functionality.

Tests:
- Vector search (semantic similarity)
- Keyword search (fulltext index)
- Graph search (relationship traversal)
- L0/L1 search (Redis)
- RRF fusion (result merging)
"""

import asyncio
import uuid
from typing import List, Optional

from ..core.base_checker import RuntimeTester
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class RetrievalTester(RuntimeTester):
    """Тестирование системы поиска с реальными базами данных."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="RetrievalTester", timeout_seconds=config.runtime_test_timeout_seconds)
        self.config = config
        self.memory = None
        self.retriever = None
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки поиска."""
        issues = []
        
        # Initialize connections
        try:
            await self._initialize_connections()
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.CRITICAL,
                title="Cannot initialize retrieval system",
                description=f"Failed to connect to databases: {str(e)}",
                location="RetrievalTester",
                impact="Cannot test retrieval functionality",
                recommendation="Check Neo4j and Redis connections",
            ))
            return issues
        
        try:
            # Test vector search
            self.logger.info("Testing vector search...")
            result = await self.test_vector_search()
            issues.extend(result.issues)
            
            # Test keyword search
            self.logger.info("Testing keyword search...")
            result = await self.test_keyword_search()
            issues.extend(result.issues)
            
            # Test graph search
            self.logger.info("Testing graph search...")
            result = await self.test_graph_search()
            issues.extend(result.issues)
            
            # Test L0/L1 search
            self.logger.info("Testing L0/L1 search...")
            result = await self.test_l0_l1_search()
            issues.extend(result.issues)
            
            # Test RRF fusion
            self.logger.info("Testing RRF fusion...")
            result = await self.test_rrf_fusion()
            issues.extend(result.issues)
        
        finally:
            await self._cleanup_connections()
        
        return issues
    
    async def _initialize_connections(self):
        """Инициализировать подключения."""
        try:
            import sys
            
            # Add src to path
            src_path = self.config.src_dir
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            # Try to import FractalMemory and HybridRetriever
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
                
                # Try to get retriever
                if hasattr(self.memory, 'retriever'):
                    self.retriever = self.memory.retriever
                elif hasattr(self.memory, '_retriever'):
                    self.retriever = self.memory._retriever
            
            except ImportError as e:
                self.logger.warning(f"Cannot import FractalMemory: {e}")
        
        except Exception as e:
            self.logger.error(f"Error initializing connections: {e}")
            raise
    
    async def _cleanup_connections(self):
        """Закрыть все подключения."""
        try:
            if self.memory:
                await self.memory.close()
        except Exception as e:
            self.logger.warning(f"Error cleaning up connections: {e}")
    
    async def test_vector_search(self) -> 'TestResult':
        """
        Тест vector search (семантический поиск).
        
        Проверяет что vector search возвращает релевантные результаты.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.memory:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.HIGH,
                    title="FractalMemory not available for vector search test",
                    description="Cannot test vector search without FractalMemory instance",
                    location="RetrievalTester.test_vector_search",
                    impact="Cannot verify vector search works correctly",
                    recommendation="Ensure FractalMemory is properly initialized",
                ))
                return TestResult(
                    test_name="Vector Search",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Store test data
            test_content = "The quick brown fox jumps over the lazy dog"
            
            await self.memory.remember(
                content=test_content,
                importance=0.8
            )
            
            await asyncio.sleep(1)
            
            # Search with similar query
            similar_query = "fast brown animal jumping"
            
            results = await self.memory.search(
                query=similar_query,
                limit=5
            )
            
            # Check if search works
            if results is None:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.CRITICAL,
                    title="Vector search returns None",
                    description="Search method returns None instead of results list",
                    location="Vector Search",
                    impact="Search functionality is broken",
                    recommendation="Fix search method to return empty list instead of None",
                ))
            elif len(results) == 0:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="Vector search returns no results",
                    description="Search returns empty results for similar query",
                    location="Vector Search",
                    impact="Vector search may not be working correctly",
                    recommendation="Check vector embedding and similarity search logic",
                ))
            
            # Test with exact match
            exact_results = await self.memory.search(
                query=test_content,
                limit=5
            )
            
            if exact_results is None or len(exact_results) == 0:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.HIGH,
                    title="Vector search fails on exact match",
                    description="Search returns no results for exact content match",
                    location="Vector Search",
                    impact="Basic search functionality is broken",
                    recommendation="Check search implementation and indexing",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in vector search test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.HIGH,
                title="Vector search test failed",
                description=f"Exception: {str(e)}",
                location="RetrievalTester.test_vector_search",
                impact="Cannot verify vector search works",
                recommendation="Fix the error in vector search logic",
            ))
        
        return TestResult(
            test_name="Vector Search",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_keyword_search(self) -> 'TestResult':
        """
        Тест keyword search (fulltext поиск).
        
        Проверяет что keyword search работает с fulltext индексом Neo4j.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.retriever:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="HybridRetriever not available for keyword search test",
                    description="Cannot test keyword search without HybridRetriever instance",
                    location="RetrievalTester.test_keyword_search",
                    impact="Cannot verify keyword search works correctly",
                    recommendation="Ensure HybridRetriever is accessible",
                ))
                return TestResult(
                    test_name="Keyword Search",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Test keyword search if method exists
            if hasattr(self.retriever, 'keyword_search'):
                test_query = "test keyword search"
                
                results = await self.retriever.keyword_search(
                    query=test_query,
                    user_id="test_user_keyword",
                    limit=5
                )
                
                # Check if method works
                if results is None:
                    issues.append(self.create_issue(
                        category=Category.RETRIEVAL,
                        severity=Severity.HIGH,
                        title="Keyword search returns None",
                        description="keyword_search method returns None",
                        location="Keyword Search",
                        impact="Keyword search is broken",
                        recommendation="Fix keyword_search to return empty list instead of None",
                    ))
            else:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="Keyword search method not found",
                    description="HybridRetriever doesn't have keyword_search method",
                    location="HybridRetriever",
                    impact="Keyword search functionality is missing",
                    recommendation="Implement keyword_search method in HybridRetriever",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in keyword search test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.MEDIUM,
                title="Keyword search test failed",
                description=f"Exception: {str(e)}",
                location="RetrievalTester.test_keyword_search",
                impact="Cannot verify keyword search works",
                recommendation="Fix the error in keyword search logic",
            ))
        
        return TestResult(
            test_name="Keyword Search",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_graph_search(self) -> 'TestResult':
        """
        Тест graph search (обход графа).
        
        Проверяет что graph search обходит связи правильно.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.retriever:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="HybridRetriever not available for graph search test",
                    description="Cannot test graph search without HybridRetriever instance",
                    location="RetrievalTester.test_graph_search",
                    impact="Cannot verify graph search works correctly",
                    recommendation="Ensure HybridRetriever is accessible",
                ))
                return TestResult(
                    test_name="Graph Search",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Test graph search if method exists
            if hasattr(self.retriever, 'graph_search'):
                test_query = "test graph search"
                
                results = await self.retriever.graph_search(
                    query=test_query,
                    user_id="test_user_graph",
                    limit=5
                )
                
                # Check if method works
                if results is None:
                    issues.append(self.create_issue(
                        category=Category.RETRIEVAL,
                        severity=Severity.HIGH,
                        title="Graph search returns None",
                        description="graph_search method returns None",
                        location="Graph Search",
                        impact="Graph search is broken",
                        recommendation="Fix graph_search to return empty list instead of None",
                    ))
            else:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="Graph search method not found",
                    description="HybridRetriever doesn't have graph_search method",
                    location="HybridRetriever",
                    impact="Graph search functionality is missing",
                    recommendation="Implement graph_search method in HybridRetriever",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in graph search test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.MEDIUM,
                title="Graph search test failed",
                description=f"Exception: {str(e)}",
                location="RetrievalTester.test_graph_search",
                impact="Cannot verify graph search works",
                recommendation="Fix the error in graph search logic",
            ))
        
        return TestResult(
            test_name="Graph Search",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_l0_l1_search(self) -> 'TestResult':
        """
        Тест L0/L1 search (поиск в Redis).
        
        Проверяет что поиск работает на уровнях L0 и L1 (оба в Redis).
        Реальная архитектура: L1 в Redis как memory:{user}:l1:session:{id}
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            # Проверяем Redis напрямую
            if not self.retriever:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="HybridRetriever not available for L0/L1 search test",
                    description="Cannot test L0/L1 search without HybridRetriever instance",
                    location="RetrievalTester.test_l0_l1_search",
                    impact="Cannot verify L0/L1 search works correctly",
                    recommendation="Ensure HybridRetriever is properly initialized",
                ))
                return TestResult(
                    test_name="L0/L1 Search",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Проверяем что retriever может искать в Redis L1
            # Получаем Redis client из retriever или memory
            redis_client = None
            if hasattr(self.retriever, 'redis_client'):
                redis_client = self.retriever.redis_client
            elif hasattr(self.retriever, '_redis_client'):
                redis_client = self.retriever._redis_client
            elif self.memory and hasattr(self.memory, 'redis_client'):
                redis_client = self.memory.redis_client
            
            if not redis_client:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.MEDIUM,
                    title="Redis client not accessible in retriever",
                    description="Cannot access Redis client to test L0/L1 search",
                    location="L0/L1 Search",
                    impact="Cannot verify Redis search functionality",
                    recommendation="Ensure retriever has access to Redis client",
                ))
                return TestResult(
                    test_name="L0/L1 Search",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Проверяем что можем читать L1 ключи
            l1_keys = await redis_client.keys("memory:*:l1:*")
            
            if not l1_keys:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.LOW,
                    title="No L1 keys found for search test",
                    description="Cannot test L1 search without existing L1 data",
                    location="L0/L1 Search",
                    impact="Cannot verify L1 search works (no data to search)",
                    recommendation="Ensure L1 has data before running search tests",
                ))
            else:
                self.logger.info(f"Found {len(l1_keys)} L1 keys for search testing")
                
                # Проверяем что можем читать L1 данные
                sample_key = l1_keys[0]
                l1_data = await redis_client.hgetall(sample_key)
                
                if 'summary' not in l1_data:
                    issues.append(self.create_issue(
                        category=Category.RETRIEVAL,
                        severity=Severity.MEDIUM,
                        title="L1 keys missing searchable content",
                        description="L1 keys don't have 'summary' field for search",
                        location="L1 Search",
                        impact="Cannot search L1 content",
                        recommendation="Ensure L1 keys have 'summary' field with searchable text",
                    ))
                
                # Проверяем что retriever имеет метод для поиска в L1
                has_l1_search = (
                    hasattr(self.retriever, 'search_l1') or
                    hasattr(self.retriever, '_search_l1') or
                    hasattr(self.retriever, 'search_redis') or
                    hasattr(self.retriever, 'search')  # Общий метод может включать L1
                )
                
                if not has_l1_search:
                    issues.append(self.create_issue(
                        category=Category.RETRIEVAL,
                        severity=Severity.MEDIUM,
                        title="No L1 search method found",
                        description="HybridRetriever doesn't have method to search L1 (Redis)",
                        location="L1 Search",
                        impact="Cannot search recent memories in L1",
                        recommendation="Implement search_l1 or search_redis method in HybridRetriever",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error in L0/L1 search test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.MEDIUM,
                title="L0/L1 search test failed",
                description=f"Exception: {str(e)}",
                location="RetrievalTester.test_l0_l1_search",
                impact="Cannot verify L0/L1 search works",
                recommendation="Fix the error in L0/L1 search logic",
            ))
        
        return TestResult(
            test_name="L0/L1 Search",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
    
    async def test_rrf_fusion(self) -> 'TestResult':
        """
        Тест RRF fusion (объединение результатов).
        
        Проверяет что RRF правильно объединяет результаты из разных источников.
        """
        from ..core.models import TestResult
        
        issues = []
        
        try:
            if not self.retriever:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.LOW,
                    title="HybridRetriever not available for RRF test",
                    description="Cannot test RRF fusion without HybridRetriever instance",
                    location="RetrievalTester.test_rrf_fusion",
                    impact="Cannot verify RRF fusion works correctly",
                    recommendation="Ensure HybridRetriever is accessible",
                ))
                return TestResult(
                    test_name="RRF Fusion",
                    passed=False,
                    issues=issues,
                    duration_ms=0,
                )
            
            # Test main search method (should use RRF fusion)
            if hasattr(self.retriever, 'search'):
                test_query = "test rrf fusion"
                
                results = await self.retriever.search(
                    query=test_query,
                    user_id="test_user_rrf",
                    limit=5
                )
                
                # Check if method works
                if results is None:
                    issues.append(self.create_issue(
                        category=Category.RETRIEVAL,
                        severity=Severity.HIGH,
                        title="Hybrid search returns None",
                        description="HybridRetriever.search returns None",
                        location="RRF Fusion",
                        impact="Hybrid search is broken",
                        recommendation="Fix search to return empty list instead of None",
                    ))
            else:
                issues.append(self.create_issue(
                    category=Category.RETRIEVAL,
                    severity=Severity.HIGH,
                    title="Hybrid search method not found",
                    description="HybridRetriever doesn't have search method",
                    location="HybridRetriever",
                    impact="Main search functionality is missing",
                    recommendation="Implement search method in HybridRetriever",
                ))
        
        except Exception as e:
            self.logger.error(f"Error in RRF fusion test: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.RETRIEVAL,
                severity=Severity.MEDIUM,
                title="RRF fusion test failed",
                description=f"Exception: {str(e)}",
                location="RetrievalTester.test_rrf_fusion",
                impact="Cannot verify RRF fusion works",
                recommendation="Fix the error in RRF fusion logic",
            ))
        
        return TestResult(
            test_name="RRF Fusion",
            passed=len(issues) == 0,
            issues=issues,
            duration_ms=0,
        )
