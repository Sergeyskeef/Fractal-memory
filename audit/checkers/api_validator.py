"""
API validator for checking consistency between components.

Checks:
- SearchResult format consistency
- FractalMemory API compatibility
- HybridRetriever API compatibility
- FastAPI endpoint response formats
"""

import ast
import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from ..core.base_checker import StaticChecker
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class APIValidator(StaticChecker):
    """Проверка консистентности API между компонентами."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="APIValidator", timeout_seconds=config.default_timeout_seconds)
        self.config = config
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки API."""
        issues = []
        
        # Check SearchResult format consistency
        self.logger.info("Checking SearchResult format...")
        issues.extend(await self.check_search_result_format())
        
        # Check FractalMemory API
        self.logger.info("Checking FractalMemory API...")
        issues.extend(await self.check_memory_api())
        
        # Check HybridRetriever API
        self.logger.info("Checking HybridRetriever API...")
        issues.extend(await self.check_retriever_api())
        
        # Check FastAPI endpoints
        self.logger.info("Checking FastAPI endpoints...")
        issues.extend(await self.check_fastapi_endpoints())
        
        return issues
    
    async def check_search_result_format(self) -> List[Issue]:
        """
        Проверить консистентность формата SearchResult.
        
        SearchResult используется в разных компонентах и должен быть согласован.
        
        Returns:
            Список проблем с форматом SearchResult
        """
        issues = []
        
        try:
            # Find all definitions of SearchResult
            search_result_defs = self._find_class_definitions('SearchResult')
            
            if len(search_result_defs) == 0:
                issues.append(self.create_issue(
                    category=Category.API,
                    severity=Severity.HIGH,
                    title="SearchResult class not found",
                    description="Could not find SearchResult class definition",
                    location="project",
                    impact="Cannot validate SearchResult consistency",
                    recommendation="Ensure SearchResult is defined in the codebase",
                ))
                return issues
            
            if len(search_result_defs) > 1:
                locations = ', '.join([f"{path}:{line}" for path, line, _ in search_result_defs])
                issues.append(self.create_issue(
                    category=Category.API,
                    severity=Severity.HIGH,
                    title="Multiple SearchResult definitions found",
                    description=f"Found {len(search_result_defs)} definitions of SearchResult",
                    location=locations,
                    impact="Different components may use incompatible SearchResult formats",
                    recommendation="Consolidate to a single SearchResult definition",
                ))
            
            # Extract fields from each definition
            for file_path, line_no, class_node in search_result_defs:
                fields = self._extract_dataclass_fields(class_node)
                
                # Check for required fields
                required_fields = {'content', 'score', 'metadata'}
                missing_fields = required_fields - set(fields.keys())
                
                if missing_fields:
                    issues.append(self.create_issue(
                        category=Category.API,
                        severity=Severity.HIGH,
                        title=f"SearchResult missing required fields",
                        description=f"SearchResult at {file_path}:{line_no} missing fields: {', '.join(missing_fields)}",
                        location=f"{file_path}:{line_no}",
                        impact="Components may fail when accessing missing fields",
                        recommendation=f"Add missing fields: {', '.join(missing_fields)}",
                    ))
        
        except Exception as e:
            self.logger.warning(f"Error checking SearchResult format: {e}")
            issues.append(self.create_issue(
                category=Category.API,
                severity=Severity.MEDIUM,
                title="Failed to check SearchResult format",
                description=f"Error: {str(e)}",
                location="APIValidator",
                impact="Cannot validate SearchResult consistency",
                recommendation="Check if SearchResult is properly defined",
            ))
        
        return issues
    
    async def check_memory_api(self) -> List[Issue]:
        """
        Проверить API FractalMemory.
        
        Returns:
            Список проблем с API памяти
        """
        issues = []
        
        try:
            # Find FractalMemory class
            memory_defs = self._find_class_definitions('FractalMemory')
            
            if len(memory_defs) == 0:
                issues.append(self.create_issue(
                    category=Category.API,
                    severity=Severity.CRITICAL,
                    title="FractalMemory class not found",
                    description="Could not find FractalMemory class definition",
                    location="project",
                    impact="Core memory system is missing",
                    recommendation="Ensure FractalMemory is defined in src/",
                ))
                return issues
            
            # Check for required methods
            file_path, line_no, class_node = memory_defs[0]
            methods = self._extract_class_methods(class_node)
            
            required_methods = {
                'remember': 'Store new memory',
                'search': 'Search memories',
                'consolidate': 'Consolidate memories between levels',
                'get_stats': 'Get memory statistics',
            }
            
            for method_name, description in required_methods.items():
                if method_name not in methods:
                    issues.append(self.create_issue(
                        category=Category.API,
                        severity=Severity.HIGH,
                        title=f"FractalMemory missing method: {method_name}",
                        description=f"Required method '{method_name}' ({description}) not found",
                        location=f"{file_path}:{line_no}",
                        impact=f"Cannot {description.lower()}",
                        recommendation=f"Implement {method_name}() method",
                    ))
            
            # Check method signatures
            if 'remember' in methods:
                remember_sig = methods['remember']
                if 'content' not in remember_sig.get('params', []):
                    issues.append(self.create_issue(
                        category=Category.API,
                        severity=Severity.MEDIUM,
                        title="FractalMemory.remember() missing 'content' parameter",
                        description="remember() should accept 'content' parameter",
                        location=f"{file_path}:{remember_sig.get('line_no', line_no)}",
                        impact="Cannot store memory content",
                        recommendation="Add 'content' parameter to remember()",
                    ))
        
        except Exception as e:
            self.logger.warning(f"Error checking FractalMemory API: {e}")
        
        return issues
    
    async def check_retriever_api(self) -> List[Issue]:
        """
        Проверить API HybridRetriever.
        
        Returns:
            Список проблем с API retriever
        """
        issues = []
        
        try:
            # Find HybridRetriever class
            retriever_defs = self._find_class_definitions('HybridRetriever')
            
            if len(retriever_defs) == 0:
                issues.append(self.create_issue(
                    category=Category.API,
                    severity=Severity.HIGH,
                    title="HybridRetriever class not found",
                    description="Could not find HybridRetriever class definition",
                    location="project",
                    impact="Hybrid search functionality is missing",
                    recommendation="Ensure HybridRetriever is defined in src/",
                ))
                return issues
            
            # Check for required methods
            file_path, line_no, class_node = retriever_defs[0]
            methods = self._extract_class_methods(class_node)
            
            required_methods = {
                'search': 'Perform hybrid search',
                # Note: vector_search, keyword_search, graph_search are private methods (_method_name)
                # They are implementation details, not part of public API
            }
            
            for method_name, description in required_methods.items():
                if method_name not in methods:
                    issues.append(self.create_issue(
                        category=Category.API,
                        severity=Severity.MEDIUM,
                        title=f"HybridRetriever missing method: {method_name}",
                        description=f"Expected method '{method_name}' ({description}) not found",
                        location=f"{file_path}:{line_no}",
                        impact=f"Cannot perform {description.lower()}",
                        recommendation=f"Implement {method_name}() method",
                    ))
        
        except Exception as e:
            self.logger.warning(f"Error checking HybridRetriever API: {e}")
        
        return issues
    
    async def check_fastapi_endpoints(self) -> List[Issue]:
        """
        Проверить FastAPI endpoints.
        
        Returns:
            Список проблем с endpoints
        """
        issues = []
        
        try:
            # Find FastAPI router files
            backend_dir = self.config.backend_dir
            router_files = list(backend_dir.glob('routers/**/*.py'))
            
            if not router_files:
                issues.append(self.create_issue(
                    category=Category.API,
                    severity=Severity.MEDIUM,
                    title="No FastAPI router files found",
                    description=f"No router files found in {backend_dir}/routers/",
                    location=str(backend_dir),
                    impact="API endpoints may not be defined",
                    recommendation="Check if routers are in the correct location",
                ))
                return issues
            
            # Check each router file
            for router_file in router_files:
                file_issues = await self._check_router_file(router_file)
                issues.extend(file_issues)
        
        except Exception as e:
            self.logger.warning(f"Error checking FastAPI endpoints: {e}")
        
        return issues
    
    async def _check_router_file(self, file_path: Path) -> List[Issue]:
        """Проверить файл с FastAPI роутером."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Find route decorators (support both sync and async functions)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if function has route decorator
                    for decorator in node.decorator_list:
                        if self._is_route_decorator(decorator):
                            # Check response model
                            if not self._has_response_model(decorator):
                                issues.append(self.create_issue(
                                    category=Category.API,
                                    severity=Severity.LOW,
                                    title=f"Endpoint missing response_model: {node.name}",
                                    description=f"Endpoint '{node.name}' doesn't specify response_model",
                                    location=f"{file_path}:{node.lineno}",
                                    impact="Response format is not validated",
                                    recommendation="Add response_model parameter to route decorator",
                                ))
        
        except Exception as e:
            self.logger.warning(f"Error checking router file {file_path}: {e}")
        
        return issues
    
    def _find_class_definitions(self, class_name: str) -> List[tuple]:
        """
        Найти все определения класса в проекте.
        
        Args:
            class_name: Имя класса
        
        Returns:
            Список (file_path, line_no, class_node)
        """
        results = []
        
        python_files = self.config.get_python_files()
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content, filename=str(file_path))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        results.append((file_path, node.lineno, node))
            
            except Exception:
                continue
        
        return results
    
    def _extract_dataclass_fields(self, class_node: ast.ClassDef) -> Dict[str, Any]:
        """Извлечь поля из dataclass."""
        fields = {}
        
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                field_name = node.target.id
                field_type = ast.unparse(node.annotation) if hasattr(ast, 'unparse') else 'unknown'
                fields[field_name] = field_type
        
        return fields
    
    def _extract_class_methods(self, class_node: ast.ClassDef) -> Dict[str, Dict[str, Any]]:
        """Извлечь методы класса."""
        methods = {}
        
        for node in class_node.body:
            # Support both sync and async methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = [arg.arg for arg in node.args.args]
                methods[node.name] = {
                    'params': params,
                    'line_no': node.lineno,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                }
        
        return methods
    
    def _is_route_decorator(self, decorator: ast.expr) -> bool:
        """Проверить, является ли декоратор роутом FastAPI."""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                # router.get, router.post, etc.
                return decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']
        
        return False
    
    def _has_response_model(self, decorator: ast.Call) -> bool:
        """Проверить наличие response_model в декораторе."""
        for keyword in decorator.keywords:
            if keyword.arg == 'response_model':
                return True
        
        return False
