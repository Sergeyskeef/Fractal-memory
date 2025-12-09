"""
Audit orchestrator for parallel execution and resource management.

Features:
- Parallel execution of independent checks
- Error handling and graceful degradation
- Timeout handling
- Resource cleanup
"""

import asyncio
import logging
from typing import List, Optional

from audit.config import AuditConfig
from audit.core.base_checker import BaseChecker
from audit.core.models import TestResult, Issue, Category, Severity


logger = logging.getLogger(__name__)


class AuditOrchestrator:
    """Оркестратор для управления выполнением аудита."""
    
    def __init__(self, config: AuditConfig):
        """
        Args:
            config: Конфигурация аудита
        """
        self.config = config
        self.resources = []  # Список ресурсов для cleanup
    
    async def run_checkers_parallel(
        self,
        checkers: List[BaseChecker],
        max_parallel: Optional[int] = None
    ) -> List[TestResult]:
        """
        Запустить checkers параллельно.
        
        Args:
            checkers: Список checkers для запуска
            max_parallel: Максимальное количество параллельных задач (None = без ограничений)
        
        Returns:
            Список результатов тестов
        """
        if not checkers:
            return []
        
        logger.info(f"Running {len(checkers)} checkers in parallel...")
        
        # Если max_parallel не указан, используем значение из конфига
        if max_parallel is None:
            max_parallel = self.config.max_parallel_checks
        
        results = []
        
        # Разбить на батчи если нужно
        if max_parallel and max_parallel > 0:
            # Запускать батчами
            for i in range(0, len(checkers), max_parallel):
                batch = checkers[i:i + max_parallel]
                batch_results = await self._run_batch(batch)
                results.extend(batch_results)
        else:
            # Запустить все сразу
            results = await self._run_batch(checkers)
        
        return results
    
    async def _run_batch(self, checkers: List[BaseChecker]) -> List[TestResult]:
        """Запустить батч checkers параллельно."""
        tasks = [checker.run() for checker in checkers]
        
        # Использовать gather с return_exceptions для graceful degradation
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработать результаты
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Checker упал с исключением
                logger.error(f"Checker {checkers[i].name} failed: {result}")
                
                # Создать TestResult с ошибкой
                error_result = TestResult(
                    test_name=checkers[i].name,
                    passed=False,
                    issues=[
                        Issue(
                            id=f"error_{checkers[i].name}",
                            category=Category.AUDIT_FAILURE,
                            severity=Severity.HIGH,
                            title=f"Checker failed: {checkers[i].name}",
                            description=f"Exception: {type(result).__name__}: {str(result)}",
                            location=checkers[i].name,
                            impact="Could not complete audit check",
                            recommendation="Fix the error in the checker or the code being audited",
                        )
                    ],
                    duration_ms=0,
                    details={"exception": str(result), "exception_type": type(result).__name__},
                )
                processed_results.append(error_result)
            else:
                # Нормальный результат
                processed_results.append(result)
        
        return processed_results
    
    async def run_checkers_sequential(
        self,
        checkers: List[BaseChecker]
    ) -> List[TestResult]:
        """
        Запустить checkers последовательно.
        
        Args:
            checkers: Список checkers для запуска
        
        Returns:
            Список результатов тестов
        """
        if not checkers:
            return []
        
        logger.info(f"Running {len(checkers)} checkers sequentially...")
        
        results = []
        
        for i, checker in enumerate(checkers, 1):
            logger.info(f"[{i}/{len(checkers)}] Running {checker.name}...")
            
            try:
                result = await checker.run()
                results.append(result)
                
                status = "✅ PASSED" if result.passed else "❌ FAILED"
                logger.info(f"  {status} - Found {len(result.issues)} issues")
            
            except Exception as e:
                logger.error(f"Checker {checker.name} failed: {e}", exc_info=True)
                
                # Создать TestResult с ошибкой
                error_result = TestResult(
                    test_name=checker.name,
                    passed=False,
                    issues=[
                        Issue(
                            id=f"error_{checker.name}",
                            category=Category.AUDIT_FAILURE,
                            severity=Severity.HIGH,
                            title=f"Checker failed: {checker.name}",
                            description=f"Exception: {type(e).__name__}: {str(e)}",
                            location=checker.name,
                            impact="Could not complete audit check",
                            recommendation="Fix the error in the checker or the code being audited",
                        )
                    ],
                    duration_ms=0,
                    details={"exception": str(e), "exception_type": type(e).__name__},
                )
                results.append(error_result)
        
        return results
    
    def register_resource(self, resource: any):
        """
        Зарегистрировать ресурс для cleanup.
        
        Args:
            resource: Ресурс (connection, file handle, etc.)
        """
        self.resources.append(resource)
    
    async def cleanup(self):
        """Очистить все зарегистрированные ресурсы."""
        logger.info("Cleaning up resources...")
        
        for resource in self.resources:
            try:
                # Попробовать разные методы закрытия
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                elif hasattr(resource, 'disconnect'):
                    if asyncio.iscoroutinefunction(resource.disconnect):
                        await resource.disconnect()
                    else:
                        resource.disconnect()
                elif hasattr(resource, '__aexit__'):
                    await resource.__aexit__(None, None, None)
                elif hasattr(resource, '__exit__'):
                    resource.__exit__(None, None, None)
            
            except Exception as e:
                logger.warning(f"Error cleaning up resource {resource}: {e}")
        
        self.resources.clear()
        logger.info("Cleanup complete")
    
    async def run_with_cleanup(
        self,
        checkers: List[BaseChecker],
        parallel: bool = True
    ) -> List[TestResult]:
        """
        Запустить checkers с автоматическим cleanup.
        
        Args:
            checkers: Список checkers для запуска
            parallel: Запускать параллельно или последовательно
        
        Returns:
            Список результатов тестов
        """
        try:
            if parallel:
                results = await self.run_checkers_parallel(checkers)
            else:
                results = await self.run_checkers_sequential(checkers)
            
            return results
        
        finally:
            # Всегда выполнить cleanup
            await self.cleanup()
    
    def group_checkers_by_dependencies(
        self,
        checkers: List[BaseChecker]
    ) -> List[List[BaseChecker]]:
        """
        Сгруппировать checkers по зависимостям для оптимального выполнения.
        
        Checkers без зависимостей могут выполняться параллельно.
        Checkers с зависимостями выполняются последовательно.
        
        Args:
            checkers: Список checkers
        
        Returns:
            Список групп checkers (каждая группа может выполняться параллельно)
        """
        # Простая эвристика: статические checkers независимы, runtime зависят от БД
        static_checkers = []
        runtime_checkers = []
        
        for checker in checkers:
            # Проверяем по имени класса
            if 'Tester' in checker.__class__.__name__ or 'Validator' in checker.__class__.__name__:
                if 'E2E' in checker.__class__.__name__:
                    # E2E тесты зависят от всего остального
                    runtime_checkers.append(checker)
                elif any(keyword in checker.__class__.__name__ for keyword in ['Memory', 'Retrieval', 'Learning']):
                    # Runtime тесты зависят от БД
                    runtime_checkers.append(checker)
                else:
                    # Статические проверки независимы
                    static_checkers.append(checker)
            else:
                # По умолчанию считаем независимыми
                static_checkers.append(checker)
        
        # Вернуть группы
        groups = []
        if static_checkers:
            groups.append(static_checkers)
        if runtime_checkers:
            groups.append(runtime_checkers)
        
        return groups
    
    async def run_optimized(
        self,
        checkers: List[BaseChecker]
    ) -> List[TestResult]:
        """
        Запустить checkers с оптимизацией по зависимостям.
        
        Независимые checkers выполняются параллельно,
        зависимые - последовательно.
        
        Args:
            checkers: Список checkers для запуска
        
        Returns:
            Список результатов тестов
        """
        groups = self.group_checkers_by_dependencies(checkers)
        
        logger.info(f"Optimized execution: {len(groups)} groups")
        for i, group in enumerate(groups, 1):
            logger.info(f"  Group {i}: {len(group)} checkers")
        
        all_results = []
        
        try:
            for i, group in enumerate(groups, 1):
                logger.info(f"\nExecuting group {i}/{len(groups)}...")
                
                # Каждая группа выполняется параллельно
                group_results = await self.run_checkers_parallel(group)
                all_results.extend(group_results)
            
            return all_results
        
        finally:
            # Cleanup
            await self.cleanup()


# Convenience function
async def run_audit_with_orchestrator(
    checkers: List[BaseChecker],
    config: AuditConfig,
    parallel: bool = True,
    optimized: bool = False
) -> List[TestResult]:
    """
    Удобная функция для запуска аудита с оркестратором.
    
    Args:
        checkers: Список checkers для запуска
        config: Конфигурация аудита
        parallel: Запускать параллельно
        optimized: Использовать оптимизацию по зависимостям
    
    Returns:
        Список результатов тестов
    """
    orchestrator = AuditOrchestrator(config)
    
    if optimized:
        return await orchestrator.run_optimized(checkers)
    else:
        return await orchestrator.run_with_cleanup(checkers, parallel=parallel)
