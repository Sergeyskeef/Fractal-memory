"""
Config validator for checking system configuration.

Checks:
- Environment variables (.env)
- Docker Compose configuration
- Migrations status
- Configuration consistency
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from ..core.base_checker import StaticChecker
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class ConfigValidator(StaticChecker):
    """Проверка конфигурации системы."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="ConfigValidator", timeout_seconds=config.default_timeout_seconds)
        self.config = config
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки конфигурации."""
        issues = []
        
        # Check environment variables
        self.logger.info("Checking environment variables...")
        issues.extend(await self.check_env_variables())
        
        # Check Docker Compose
        self.logger.info("Checking Docker Compose configuration...")
        issues.extend(await self.check_docker_compose())
        
        # Check migrations
        self.logger.info("Checking migrations...")
        issues.extend(await self.check_migrations())
        
        # Check backend config
        self.logger.info("Checking backend configuration...")
        issues.extend(await self.check_backend_config())
        
        return issues
    
    async def check_env_variables(self) -> List[Issue]:
        """
        Проверить переменные окружения.
        
        Validates: Requirements 6.1
        """
        issues = []
        
        try:
            # Check .env file
            env_file = self.config.project_root / ".env"
            env_example = self.config.project_root / ".env.example"
            
            if not env_file.exists():
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.HIGH,
                    title=".env file not found",
                    description=f"Expected .env at {env_file}",
                    location=str(self.config.project_root),
                    impact="Application may not have required configuration",
                    recommendation="Create .env file from .env.example",
                ))
                
                # If .env doesn't exist, check .env.example
                if env_example.exists():
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title=".env.example exists but .env missing",
                        description="Copy .env.example to .env and fill in values",
                        location=str(self.config.project_root),
                        impact="Configuration template exists but not used",
                        recommendation="cp .env.example .env",
                    ))
                
                return issues
            
            # Parse .env file
            env_vars = self._parse_env_file(env_file)
            
            # Required variables
            required_vars = {
                'NEO4J_URI': 'Neo4j connection URI',
                'NEO4J_USER': 'Neo4j username',
                'NEO4J_PASSWORD': 'Neo4j password',
                'REDIS_URL': 'Redis connection URL',
                'OPENAI_API_KEY': 'OpenAI API key for embeddings',
            }
            
            # Check for missing or empty required variables
            for var_name, description in required_vars.items():
                if var_name not in env_vars:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.CRITICAL,
                        title=f"Missing required environment variable: {var_name}",
                        description=f"{description} not found in .env",
                        location=str(env_file),
                        impact=f"Application cannot connect to {description.lower()}",
                        recommendation=f"Add {var_name} to .env file",
                    ))
                elif not env_vars[var_name] or env_vars[var_name].strip() == '':
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.CRITICAL,
                        title=f"Empty environment variable: {var_name}",
                        description=f"{description} is empty in .env",
                        location=str(env_file),
                        impact=f"Application cannot connect to {description.lower()}",
                        recommendation=f"Set value for {var_name} in .env file",
                    ))
            
            # Check for placeholder values
            placeholder_patterns = [
                'your_',
                'changeme',
                'password',
                'secret',
                'example',
            ]
            
            for var_name, var_value in env_vars.items():
                if var_name in required_vars:
                    value_lower = var_value.lower()
                    for pattern in placeholder_patterns:
                        if pattern in value_lower:
                            issues.append(self.create_issue(
                                category=Category.CONFIG,
                                severity=Severity.HIGH,
                                title=f"Placeholder value in {var_name}",
                                description=f"{var_name} appears to have placeholder value: {var_value}",
                                location=str(env_file),
                                impact="Application may not work with placeholder values",
                                recommendation=f"Replace placeholder with actual value for {var_name}",
                            ))
                            break
            
            # Check .env.example if it exists
            if env_example.exists():
                example_vars = self._parse_env_file(env_example)
                
                # Check if .env has all variables from .env.example
                missing_in_env = set(example_vars.keys()) - set(env_vars.keys())
                if missing_in_env:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title="Variables in .env.example missing from .env",
                        description=f"Missing: {', '.join(missing_in_env)}",
                        location=str(env_file),
                        impact="Some configuration may be missing",
                        recommendation="Add missing variables from .env.example to .env",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error checking environment variables: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.CONFIG,
                severity=Severity.MEDIUM,
                title="Failed to check environment variables",
                description=f"Error: {str(e)}",
                location="ConfigValidator",
                impact="Cannot validate environment configuration",
                recommendation="Check .env file is readable",
            ))
        
        return issues
    
    async def check_docker_compose(self) -> List[Issue]:
        """
        Проверить конфигурацию Docker Compose.
        
        Validates: Requirements 6.2
        """
        issues = []
        
        try:
            # Check docker-compose.yml
            compose_file = self.config.project_root / "docker-compose.yml"
            
            if not compose_file.exists():
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.HIGH,
                    title="docker-compose.yml not found",
                    description=f"Expected docker-compose.yml at {compose_file}",
                    location=str(self.config.project_root),
                    impact="Cannot run services with Docker Compose",
                    recommendation="Create docker-compose.yml for services",
                ))
                return issues
            
            with open(compose_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required services
            required_services = {
                'neo4j': 'Neo4j graph database',
                'redis': 'Redis cache',
            }
            
            for service_name, description in required_services.items():
                if service_name not in content:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.HIGH,
                        title=f"Missing service in docker-compose.yml: {service_name}",
                        description=f"{description} not defined in docker-compose.yml",
                        location=str(compose_file),
                        impact=f"Cannot run {description} with Docker Compose",
                        recommendation=f"Add {service_name} service to docker-compose.yml",
                    ))
            
            # Check Neo4j configuration
            if 'neo4j' in content:
                # Check for password
                if 'NEO4J_AUTH' not in content and 'NEO4J_PASSWORD' not in content:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.HIGH,
                        title="Neo4j password not configured in docker-compose.yml",
                        description="NEO4J_AUTH or NEO4J_PASSWORD not set",
                        location=str(compose_file),
                        impact="Neo4j may not start or use default password",
                        recommendation="Set NEO4J_AUTH environment variable",
                    ))
                
                # Check for ports
                if '7687' not in content:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title="Neo4j bolt port not exposed",
                        description="Port 7687 not found in neo4j service",
                        location=str(compose_file),
                        impact="Cannot connect to Neo4j from host",
                        recommendation="Expose port 7687:7687 in neo4j service",
                    ))
                
                # Check for volumes
                if 'volumes' not in content or 'neo4j' not in content.split('volumes')[0]:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title="Neo4j volumes not configured",
                        description="No volumes defined for neo4j service",
                        location=str(compose_file),
                        impact="Neo4j data will be lost on container restart",
                        recommendation="Add volumes for neo4j data persistence",
                    ))
            
            # Check Redis configuration
            if 'redis' in content:
                # Check for port
                if '6379' not in content:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title="Redis port not exposed",
                        description="Port 6379 not found in redis service",
                        location=str(compose_file),
                        impact="Cannot connect to Redis from host",
                        recommendation="Expose port 6379:6379 in redis service",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error checking docker-compose.yml: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.CONFIG,
                severity=Severity.MEDIUM,
                title="Failed to check docker-compose.yml",
                description=f"Error: {str(e)}",
                location="ConfigValidator",
                impact="Cannot validate Docker Compose configuration",
                recommendation="Check docker-compose.yml is readable",
            ))
        
        return issues
    
    async def check_migrations(self) -> List[Issue]:
        """
        Проверить миграции базы данных.
        
        Validates: Requirements 6.4
        """
        issues = []
        
        try:
            # Check migrations directory
            migrations_dir = self.config.project_root / "migrations"
            
            if not migrations_dir.exists():
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.MEDIUM,
                    title="Migrations directory not found",
                    description=f"Expected migrations at {migrations_dir}",
                    location=str(self.config.project_root),
                    impact="Database schema may not be initialized",
                    recommendation="Create migrations/ directory with schema migrations",
                ))
                return issues
            
            # Find migration files
            migration_files = list(migrations_dir.glob('*.cypher'))
            
            if not migration_files:
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.MEDIUM,
                    title="No migration files found",
                    description="No .cypher files in migrations/",
                    location=str(migrations_dir),
                    impact="Database schema may not be initialized",
                    recommendation="Create Cypher migration files",
                ))
            else:
                self.logger.info(f"Found {len(migration_files)} migration files")
                
                # Check for initial schema migration
                has_initial = any('initial' in f.name.lower() or '001' in f.name for f in migration_files)
                
                if not has_initial:
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title="No initial schema migration found",
                        description="Expected migration file with 'initial' or '001' in name",
                        location=str(migrations_dir),
                        impact="Database schema may not be properly initialized",
                        recommendation="Create initial schema migration",
                    ))
                
                # Check for migration runner
                run_migrations = migrations_dir / "run_migrations.py"
                
                if not run_migrations.exists():
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.LOW,
                        title="Migration runner not found",
                        description="No run_migrations.py script found",
                        location=str(migrations_dir),
                        impact="Migrations must be run manually",
                        recommendation="Create run_migrations.py script",
                    ))
        
        except Exception as e:
            self.logger.error(f"Error checking migrations: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.CONFIG,
                severity=Severity.MEDIUM,
                title="Failed to check migrations",
                description=f"Error: {str(e)}",
                location="ConfigValidator",
                impact="Cannot validate migrations",
                recommendation="Check migrations directory is accessible",
            ))
        
        return issues
    
    async def check_backend_config(self) -> List[Issue]:
        """
        Проверить конфигурацию backend.
        
        Validates: Requirements 6.3
        """
        issues = []
        
        try:
            # Check backend/config.py
            config_file = self.config.backend_dir / "config.py"
            
            if not config_file.exists():
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.HIGH,
                    title="Backend config.py not found",
                    description=f"Expected config.py at {config_file}",
                    location=str(self.config.backend_dir),
                    impact="Backend may not have configuration",
                    recommendation="Create backend/config.py with Settings class",
                ))
                return issues
            
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for Settings class
            if 'Settings' not in content and 'Config' not in content:
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.HIGH,
                    title="No Settings class in backend config",
                    description="Expected Settings or Config class in config.py",
                    location=str(config_file),
                    impact="Backend configuration not structured",
                    recommendation="Create Settings class with configuration",
                ))
            
            # Check for required configuration fields
            required_fields = {
                'neo4j': 'Neo4j connection settings',
                'redis': 'Redis connection settings',
                'openai': 'OpenAI API settings',
            }
            
            for field_name, description in required_fields.items():
                if field_name.lower() not in content.lower():
                    issues.append(self.create_issue(
                        category=Category.CONFIG,
                        severity=Severity.MEDIUM,
                        title=f"Backend config missing {field_name} settings",
                        description=f"{description} not found in config.py",
                        location=str(config_file),
                        impact=f"Backend may not configure {description.lower()}",
                        recommendation=f"Add {field_name} configuration to Settings",
                    ))
            
            # Check for BaseSettings (Pydantic)
            if 'BaseSettings' not in content:
                issues.append(self.create_issue(
                    category=Category.CONFIG,
                    severity=Severity.LOW,
                    title="Backend config not using Pydantic BaseSettings",
                    description="Settings class should inherit from BaseSettings",
                    location=str(config_file),
                    impact="Configuration may not load from environment",
                    recommendation="Use Pydantic BaseSettings for configuration",
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking backend config: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.CONFIG,
                severity=Severity.MEDIUM,
                title="Failed to check backend configuration",
                description=f"Error: {str(e)}",
                location="ConfigValidator",
                impact="Cannot validate backend configuration",
                recommendation="Check backend/config.py is accessible",
            ))
        
        return issues
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """
        Парсинг .env файла.
        
        Returns:
            Dict[variable_name, value]
        """
        env_vars = {}
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        env_vars[key] = value
        
        except Exception as e:
            self.logger.warning(f"Error parsing .env file: {e}")
        
        return env_vars
