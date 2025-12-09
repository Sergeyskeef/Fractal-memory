"""
Base classes for audit checkers and testers.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import List

from .models import Issue, TestResult, Severity, Category

logger = logging.getLogger(__name__)


class BaseChecker(ABC):
    """
    Базовый класс для всех checkers и testers.
    
    Предоставляет:
    - Шаблон метода run()
    - Error handling
    - Timeout support
    - Логирование
    """
    
    def __init__(self, name: str, timeout_seconds: float = 30.0):
        """
        Args:
            name: Имя checker'а (для логирования и отчётов)
            timeout_seconds: Таймаут выполнения (по умолчанию 30 секунд)
        """
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(f"audit.{name}")
    
    async def run(self) -> TestResult:
        """
        Запустить проверку с error handling и timeout.
        
        Returns:
            TestResult с найденными проблемами
        """
        self.logger.info(f"Starting {self.name}...")
        start_time = time.perf_counter()
        
        try:
            # Запустить с таймаутом
            issues = await asyncio.wait_for(
                self._check(),
                timeout=self.timeout_seconds
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            passed = len([i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0
            
            self.logger.info(
                f"Completed {self.name}: "
                f"found {len(issues)} issues, "
                f"passed={passed}, "
                f"duration={duration_ms:.2f}ms"
            )
            
            return TestResult(
                test_name=self.name,
                passed=passed,
                issues=issues,
                duration_ms=duration_ms,
                details={"timeout_seconds": self.timeout_seconds},
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"{self.name} timed out after {self.timeout_seconds}s")
            
            return TestResult(
                test_name=self.name,
                passed=False,
                issues=[
                    Issue(
                        id=str(uuid.uuid4()),
                        category=Category.AUDIT_FAILURE,
                        severity=Severity.MEDIUM,
                        title=f"Test timed out: {self.name}",
                        description=f"Test exceeded timeout of {self.timeout_seconds} seconds",
                        location=self.name,
                        impact="Could not complete audit check",
                        recommendation=f"Increase timeout or optimize {self.name}",
                    )
                ],
                duration_ms=duration_ms,
                details={"timeout_seconds": self.timeout_seconds, "timed_out": True},
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"{self.name} failed with exception: {e}", exc_info=True)
            
            return TestResult(
                test_name=self.name,
                passed=False,
                issues=[
                    Issue(
                        id=str(uuid.uuid4()),
                        category=Category.AUDIT_FAILURE,
                        severity=Severity.HIGH,
                        title=f"Audit check failed: {self.name}",
                        description=f"Exception: {type(e).__name__}: {str(e)}",
                        location=self.name,
                        impact="Could not complete audit check",
                        recommendation=f"Fix the error in {self.name} or the code being audited",
                        metadata={"exception_type": type(e).__name__, "exception_message": str(e)},
                    )
                ],
                duration_ms=duration_ms,
                details={"exception": str(e), "exception_type": type(e).__name__},
            )
    
    @abstractmethod
    async def _check(self) -> List[Issue]:
        """
        Выполнить проверку (должен быть реализован в подклассах).
        
        Returns:
            Список найденных проблем
        """
        pass
    
    def create_issue(
        self,
        category: Category,
        severity: Severity,
        title: str,
        description: str,
        location: str,
        impact: str,
        recommendation: str,
        code_snippet: str = None,
        **metadata
    ) -> Issue:
        """
        Удобный метод для создания Issue.
        
        Args:
            category: Категория проблемы
            severity: Серьёзность
            title: Заголовок
            description: Описание
            location: Местоположение (file:line или component)
            impact: Влияние на систему
            recommendation: Рекомендация по исправлению
            code_snippet: Фрагмент кода (опционально)
            **metadata: Дополнительные метаданные
        
        Returns:
            Issue instance
        """
        return Issue(
            id=str(uuid.uuid4()),
            category=category,
            severity=severity,
            title=title,
            description=description,
            location=location,
            impact=impact,
            recommendation=recommendation,
            code_snippet=code_snippet,
            metadata=metadata,
        )


class StaticChecker(BaseChecker):
    """Базовый класс для статических проверок (без запуска кода)."""
    pass


class RuntimeTester(BaseChecker):
    """Базовый класс для runtime тестов (с запуском кода)."""
    
    def __init__(self, name: str, timeout_seconds: float = 60.0):
        """Runtime тесты обычно требуют больше времени."""
        super().__init__(name, timeout_seconds)
