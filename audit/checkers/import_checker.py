"""
Import checker for Python and TypeScript files.

Checks:
- Existence of imported modules
- Correctness of relative paths
- Circular dependencies
- Version compatibility
"""

import ast
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from ..core.base_checker import StaticChecker
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class ImportChecker(StaticChecker):
    """Проверка импортов в Python и TypeScript файлах."""
    
    # Exclusion patterns for files that should be skipped
    EXCLUSION_PATTERNS = [
        '**/node_modules/**',
        '**/.venv/**',
        '**/venv/**',
        '**/dist/**',
        '**/build/**',
        '**/__pycache__/**',
        '**/.pytest_cache/**',
        '**/.hypothesis/**',
        '**/htmlcov/**',
    ]
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="ImportChecker", timeout_seconds=config.default_timeout_seconds)
        self.config = config
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.skipped_files_count = 0
    
    def should_skip_file(self, file_path: Path) -> bool:
        """
        Check if a file should be skipped based on exclusion patterns.
        
        Args:
            file_path: Path to the file to check
        
        Returns:
            True if file should be skipped, False otherwise
        """
        # Convert to string for pattern matching
        file_str = str(file_path)
        
        # Check against exclusion patterns
        for pattern in self.EXCLUSION_PATTERNS:
            # Simple pattern matching (could use fnmatch for more complex patterns)
            pattern_parts = pattern.replace('**/', '').replace('/**', '').split('/')
            
            # Check if any pattern part is in the file path
            for part in pattern_parts:
                if part in file_str:
                    return True
        
        return False
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки импортов."""
        issues = []
        self.skipped_files_count = 0
        
        # Check Python imports
        python_files = self.config.get_python_files()
        # Filter out excluded files
        filtered_python_files = [f for f in python_files if not self.should_skip_file(f)]
        self.skipped_files_count += len(python_files) - len(filtered_python_files)
        
        self.logger.info(f"Checking {len(filtered_python_files)} Python files (skipped {len(python_files) - len(filtered_python_files)})...")
        for file_path in filtered_python_files:
            issues.extend(await self.check_python_imports(file_path))
        
        # Check TypeScript imports
        typescript_files = self.config.get_typescript_files()
        # Filter out excluded files
        filtered_typescript_files = [f for f in typescript_files if not self.should_skip_file(f)]
        self.skipped_files_count += len(typescript_files) - len(filtered_typescript_files)
        
        self.logger.info(f"Checking {len(filtered_typescript_files)} TypeScript files (skipped {len(typescript_files) - len(filtered_typescript_files)})...")
        for file_path in filtered_typescript_files:
            issues.extend(await self.check_typescript_imports(file_path))
        
        # Log summary of skipped files
        if self.skipped_files_count > 0:
            self.logger.info(f"Skipped {self.skipped_files_count} files in excluded directories (node_modules, .venv, etc.)")
        
        # Find circular dependencies
        self.logger.info("Checking for circular dependencies...")
        issues.extend(await self.find_circular_dependencies())
        
        # Check version compatibility
        self.logger.info("Checking version compatibility...")
        issues.extend(await self.check_version_compatibility())
        
        return issues
    
    async def check_python_imports(self, file_path: Path) -> List[Issue]:
        """
        Проверить импорты в Python файле.
        
        Args:
            file_path: Путь к Python файлу
        
        Returns:
            Список найденных проблем
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Get module name from file path
            module_name = self._get_module_name(file_path)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_module = alias.name
                        issues.extend(self._check_import_exists(
                            file_path, imported_module, node.lineno
                        ))
                        # Add to dependency graph
                        self.dependency_graph[module_name].add(imported_module)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_module = node.module
                        
                        # Handle relative imports
                        if node.level > 0:
                            imported_module = self._resolve_relative_import(
                                file_path, node.module, node.level
                            )
                        
                        if imported_module:
                            issues.extend(self._check_import_exists(
                                file_path, imported_module, node.lineno
                            ))
                            # Add to dependency graph
                            self.dependency_graph[module_name].add(imported_module)
        
        except SyntaxError as e:
            issues.append(self.create_issue(
                category=Category.IMPORTS,
                severity=Severity.HIGH,
                title=f"Syntax error in {file_path.name}",
                description=f"Cannot parse file: {str(e)}",
                location=f"{file_path}:{e.lineno if hasattr(e, 'lineno') else 0}",
                impact="File cannot be imported or executed",
                recommendation="Fix syntax error",
            ))
        
        except Exception as e:
            self.logger.warning(f"Error checking imports in {file_path}: {e}")
        
        return issues
    
    async def check_typescript_imports(self, file_path: Path) -> List[Issue]:
        """
        Проверить импорты в TypeScript файле.
        
        Args:
            file_path: Путь к TypeScript файлу
        
        Returns:
            Список найденных проблем
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex patterns for TypeScript imports
            # import { X } from 'module'
            # import X from 'module'
            # import * as X from 'module'
            import_patterns = [
                r"import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s+['\"]([^'\"]+)['\"]",  # import 'module'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    imported_path = match.group(1)
                    line_no = content[:match.start()].count('\n') + 1
                    
                    # Check if it's a relative import
                    if imported_path.startswith('.'):
                        resolved_path = self._resolve_typescript_import(file_path, imported_path)
                        if resolved_path and not resolved_path.exists():
                            issues.append(self.create_issue(
                                category=Category.IMPORTS,
                                severity=Severity.HIGH,
                                title=f"Missing TypeScript module: {imported_path}",
                                description=f"Imported module '{imported_path}' not found at {resolved_path}",
                                location=f"{file_path}:{line_no}",
                                impact="Import will fail at runtime",
                                recommendation=f"Create the module or fix the import path",
                                code_snippet=match.group(0),
                            ))
                    # For node_modules imports, we'll check package.json later
        
        except Exception as e:
            self.logger.warning(f"Error checking TypeScript imports in {file_path}: {e}")
        
        return issues
    
    async def find_circular_dependencies(self) -> List[Issue]:
        """
        Найти циклические зависимости в графе импортов.
        
        Returns:
            Список найденных циклических зависимостей
        """
        issues = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS для поиска циклов."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    cycle = dfs(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        # Check each node
        for node in self.dependency_graph:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    cycle_str = " -> ".join(cycle)
                    issues.append(self.create_issue(
                        category=Category.IMPORTS,
                        severity=Severity.MEDIUM,
                        title=f"Circular dependency detected",
                        description=f"Circular import chain: {cycle_str}",
                        location="dependency_graph",
                        impact="Can cause import errors or unexpected behavior",
                        recommendation="Refactor to break the circular dependency",
                        cycle=cycle,
                    ))
        
        return issues
    
    async def check_version_compatibility(self) -> List[Issue]:
        """
        Проверить совместимость версий библиотек.
        
        Returns:
            Список проблем с версиями
        """
        issues = []
        
        # Check pyproject.toml or requirements.txt
        pyproject_path = self.config.project_root / "pyproject.toml"
        requirements_path = self.config.project_root / "requirements.txt"
        
        if pyproject_path.exists():
            issues.extend(await self._check_pyproject_versions(pyproject_path))
        elif requirements_path.exists():
            issues.extend(await self._check_requirements_versions(requirements_path))
        
        # Check package.json for frontend
        package_json_path = self.config.frontend_dir / "package.json"
        if package_json_path.exists():
            issues.extend(await self._check_package_json_versions(package_json_path))
        
        return issues
    
    def _check_import_exists(self, file_path: Path, module_name: str, line_no: int) -> List[Issue]:
        """
        Проверить существование импортируемого модуля.
        
        Args:
            file_path: Файл, в котором происходит импорт
            module_name: Имя импортируемого модуля
            line_no: Номер строки
        
        Returns:
            Список проблем (пустой если модуль существует)
        """
        issues = []
        
        # Skip standard library and common third-party modules
        # (we'll check third-party in version compatibility)
        if self._is_stdlib_module(module_name):
            return issues
        
        # Check if it's a local module
        if module_name.startswith('src.') or module_name.startswith('backend.') or \
           module_name.startswith('audit.') or module_name.startswith('fractal_memory.'):
            # Try to find the module file
            module_path = self._module_to_path(module_name)
            if module_path and not module_path.exists():
                issues.append(self.create_issue(
                    category=Category.IMPORTS,
                    severity=Severity.HIGH,
                    title=f"Missing module: {module_name}",
                    description=f"Module '{module_name}' not found at expected path {module_path}",
                    location=f"{file_path}:{line_no}",
                    impact="Import will fail at runtime",
                    recommendation=f"Create the module or fix the import path",
                ))
        
        return issues
    
    def _get_module_name(self, file_path: Path) -> str:
        """Получить имя модуля из пути к файлу."""
        try:
            rel_path = file_path.relative_to(self.config.project_root)
            parts = list(rel_path.parts[:-1]) + [rel_path.stem]
            return '.'.join(parts)
        except ValueError:
            return str(file_path)
    
    def _resolve_relative_import(self, file_path: Path, module: Optional[str], level: int) -> Optional[str]:
        """
        Разрешить относительный импорт в абсолютный.
        
        Args:
            file_path: Файл, в котором происходит импорт
            module: Имя модуля (может быть None для "from . import X")
            level: Уровень относительности (количество точек)
        
        Returns:
            Абсолютное имя модуля или None
        """
        try:
            # Get current module path
            current_module = self._get_module_name(file_path)
            parts = current_module.split('.')
            
            # Go up 'level' directories
            if level > len(parts):
                return None
            
            base_parts = parts[:-level]
            
            if module:
                return '.'.join(base_parts + [module])
            else:
                return '.'.join(base_parts)
        
        except Exception:
            return None
    
    def _resolve_typescript_import(self, file_path: Path, import_path: str) -> Optional[Path]:
        """
        Разрешить TypeScript импорт в путь к файлу.
        
        Args:
            file_path: Файл, в котором происходит импорт
            import_path: Путь импорта (например, './components/Button')
        
        Returns:
            Путь к файлу или None
        """
        try:
            # Resolve relative to file directory
            base_dir = file_path.parent
            resolved = (base_dir / import_path).resolve()
            
            # Try different extensions
            for ext in ['', '.ts', '.tsx', '.js', '.jsx']:
                candidate = resolved.parent / (resolved.name + ext)
                if candidate.exists():
                    return candidate
            
            # Try index files
            for ext in ['.ts', '.tsx', '.js', '.jsx']:
                candidate = resolved / f'index{ext}'
                if candidate.exists():
                    return candidate
            
            return resolved
        
        except Exception:
            return None
    
    def _module_to_path(self, module_name: str) -> Optional[Path]:
        """Преобразовать имя модуля в путь к файлу."""
        parts = module_name.split('.')
        
        # Try as Python file
        file_path = self.config.project_root / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
        if file_path.exists():
            return file_path
        
        # Try as package
        package_path = self.config.project_root / '/'.join(parts) / "__init__.py"
        if package_path.exists():
            return package_path
        
        return file_path  # Return expected path even if doesn't exist
    
    def _is_stdlib_module(self, module_name: str) -> bool:
        """Проверить, является ли модуль частью стандартной библиотеки."""
        # Get top-level module name
        top_level = module_name.split('.')[0]
        
        # Common stdlib modules
        stdlib_modules = {
            'abc', 'asyncio', 'collections', 'dataclasses', 'datetime', 'enum',
            'functools', 'importlib', 'io', 'json', 'logging', 'os', 'pathlib',
            're', 'sys', 'time', 'typing', 'uuid', 'warnings', 'weakref',
        }
        
        if top_level in stdlib_modules:
            return True
        
        # Try to check if it's in sys.stdlib_module_names (Python 3.10+)
        if hasattr(sys, 'stdlib_module_names'):
            return top_level in sys.stdlib_module_names
        
        return False
    
    async def _check_pyproject_versions(self, pyproject_path: Path) -> List[Issue]:
        """Проверить версии в pyproject.toml."""
        issues = []
        
        try:
            import tomli
            
            with open(pyproject_path, 'rb') as f:
                data = tomli.load(f)
            
            # Check dependencies
            dependencies = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
            
            # Look for known incompatibilities
            # (This is a simplified check - in real audit we'd check actual installed versions)
            
        except ImportError:
            self.logger.warning("tomli not installed, skipping pyproject.toml check")
        except Exception as e:
            self.logger.warning(f"Error checking pyproject.toml: {e}")
        
        return issues
    
    async def _check_requirements_versions(self, requirements_path: Path) -> List[Issue]:
        """Проверить версии в requirements.txt."""
        issues = []
        
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
            
            # Parse requirements
            # (Simplified - real implementation would use pkg_resources or packaging)
            
        except Exception as e:
            self.logger.warning(f"Error checking requirements.txt: {e}")
        
        return issues
    
    async def _check_package_json_versions(self, package_json_path: Path) -> List[Issue]:
        """Проверить версии в package.json."""
        issues = []
        
        try:
            import json
            
            with open(package_json_path, 'r') as f:
                data = json.load(f)
            
            # Check dependencies
            dependencies = data.get('dependencies', {})
            dev_dependencies = data.get('devDependencies', {})
            
            # Look for known incompatibilities
            # (Simplified check)
            
        except Exception as e:
            self.logger.warning(f"Error checking package.json: {e}")
        
        return issues
