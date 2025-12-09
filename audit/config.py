"""
Configuration for audit system.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditConfig:
    """Конфигурация системы аудита."""
    
    # === Paths ===
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    src_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "src")
    backend_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "backend")
    frontend_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "fractal-memory-interface")
    tests_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "tests")
    
    # === Neo4j Connection ===
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))
    
    # === Redis Connection ===
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # === Execution Settings ===
    default_timeout_seconds: float = 30.0
    runtime_test_timeout_seconds: float = 60.0
    parallel_execution: bool = True
    max_parallel_workers: int = 4
    
    # === File Patterns ===
    python_file_patterns: List[str] = field(default_factory=lambda: [
        "**/*.py",
    ])
    
    typescript_file_patterns: List[str] = field(default_factory=lambda: [
        "**/*.ts",
        "**/*.tsx",
    ])
    
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/.pytest_cache/**",
        "**/htmlcov/**",
        "**/.venv/**",
        "**/venv/**",
        "**/.git/**",
    ])
    
    # === Report Settings ===
    report_output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "audit_reports")
    generate_markdown: bool = True
    generate_json: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        # Ensure paths are Path objects
        self.project_root = Path(self.project_root)
        self.src_dir = Path(self.src_dir)
        self.backend_dir = Path(self.backend_dir)
        self.frontend_dir = Path(self.frontend_dir)
        self.tests_dir = Path(self.tests_dir)
        self.report_output_dir = Path(self.report_output_dir)
        
        # Create report directory if it doesn't exist
        self.report_output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_python_files(self) -> List[Path]:
        """Получить все Python файлы для проверки."""
        files = []
        for pattern in self.python_file_patterns:
            files.extend(self.project_root.glob(pattern))
        
        # Exclude patterns
        filtered_files = []
        for file in files:
            should_exclude = False
            for exclude_pattern in self.exclude_patterns:
                if file.match(exclude_pattern):
                    should_exclude = True
                    break
            if not should_exclude:
                filtered_files.append(file)
        
        return filtered_files
    
    def get_typescript_files(self) -> List[Path]:
        """Получить все TypeScript файлы для проверки."""
        files = []
        for pattern in self.typescript_file_patterns:
            files.extend(self.frontend_dir.glob(pattern))
        
        # Exclude patterns
        filtered_files = []
        for file in files:
            should_exclude = False
            for exclude_pattern in self.exclude_patterns:
                if file.match(exclude_pattern):
                    should_exclude = True
                    break
            if not should_exclude:
                filtered_files.append(file)
        
        return filtered_files
    
    def has_neo4j_credentials(self) -> bool:
        """Проверить наличие Neo4j credentials."""
        return bool(self.neo4j_password)
    
    def has_redis_url(self) -> bool:
        """Проверить наличие Redis URL."""
        return bool(self.redis_url)


def get_default_config() -> AuditConfig:
    """Получить конфигурацию по умолчанию."""
    return AuditConfig()
