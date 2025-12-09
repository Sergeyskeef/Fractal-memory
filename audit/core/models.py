"""
Core data models for audit system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Severity(Enum):
    """Уровень серьёзности проблемы."""
    CRITICAL = "critical"  # Система не работает или работает неправильно
    HIGH = "high"          # Серьёзная проблема, требует исправления
    MEDIUM = "medium"      # Проблема средней важности
    LOW = "low"            # Незначительная проблема или улучшение


class Category(Enum):
    """Категория проблемы."""
    ARCHITECTURE = "architecture"      # Проблемы архитектуры
    IMPORTS = "imports"                # Проблемы с импортами
    SCHEMA = "schema"                  # Проблемы со схемой Neo4j
    API = "api"                        # Проблемы с API
    MEMORY = "memory"                  # Проблемы с памятью
    RETRIEVAL = "retrieval"            # Проблемы с поиском
    LEARNING = "learning"              # Проблемы с самообучением
    INTEGRATION = "integration"        # Проблемы интеграции
    FRONTEND = "frontend"              # Проблемы frontend
    CONFIG = "config"                  # Проблемы конфигурации
    TESTS = "tests"                    # Проблемы с тестами
    AUDIT_FAILURE = "audit_failure"    # Сбой самого аудита


@dataclass
class Issue:
    """Проблема, найденная в ходе аудита."""
    
    id: str
    category: Category
    severity: Severity
    title: str
    description: str
    location: str  # file:line или component name
    impact: str
    recommendation: str
    code_snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "code_snippet": self.code_snippet,
            "metadata": self.metadata,
        }
    
    def to_markdown(self) -> str:
        """Преобразовать в markdown для отчёта."""
        severity_emoji = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.LOW: "🟢",
        }
        
        md = f"### {severity_emoji[self.severity]} [{self.severity.value.upper()}] {self.title}\n\n"
        md += f"**Category:** {self.category.value}\n\n"
        md += f"**Location:** `{self.location}`\n\n"
        md += f"**Description:** {self.description}\n\n"
        md += f"**Impact:** {self.impact}\n\n"
        md += f"**Recommendation:** {self.recommendation}\n\n"
        
        if self.code_snippet:
            md += f"**Code:**\n```python\n{self.code_snippet}\n```\n\n"
        
        return md


@dataclass
class TestResult:
    """Результат выполнения теста."""
    
    test_name: str
    passed: bool
    issues: List[Issue]
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "issues": [issue.to_dict() for issue in self.issues],
            "duration_ms": self.duration_ms,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Neo4jSchema:
    """Схема Neo4j (реальная структура данных)."""
    
    # Метки узлов и их поля: {"Episodic": ["uuid", "content", "created_at"], ...}
    node_labels: Dict[str, List[str]]
    
    # Связи: [(from_label, rel_type, to_label), ...]
    relationships: List[Tuple[str, str, str]]
    
    # Индексы: ["index_name", ...]
    indexes: List[str]
    
    # Ограничения: ["constraint_name", ...]
    constraints: List[str]
    
    def has_node_label(self, label: str) -> bool:
        """Проверить существование метки узла."""
        return label in self.node_labels
    
    def has_node_field(self, label: str, field: str) -> bool:
        """Проверить существование поля у узла."""
        return label in self.node_labels and field in self.node_labels[label]
    
    def has_relationship(self, from_label: str, rel_type: str, to_label: str) -> bool:
        """Проверить существование связи."""
        return (from_label, rel_type, to_label) in self.relationships
    
    def has_index(self, index_name: str) -> bool:
        """Проверить существование индекса."""
        return index_name in self.indexes


@dataclass
class AuditReport:
    """Итоговый отчёт аудита."""
    
    timestamp: datetime
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues_by_category: Dict[str, int]
    test_results: List[TestResult]
    all_issues: List[Issue]
    duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_category": self.issues_by_category,
            "test_results": [tr.to_dict() for tr in self.test_results],
            "all_issues": [issue.to_dict() for issue in self.all_issues],
            "duration_seconds": self.duration_seconds,
        }
    
    def get_critical_issues(self) -> List[Issue]:
        """Получить только критические проблемы."""
        return [i for i in self.all_issues if i.severity == Severity.CRITICAL]
    
    def get_high_issues(self) -> List[Issue]:
        """Получить проблемы высокой важности."""
        return [i for i in self.all_issues if i.severity == Severity.HIGH]
