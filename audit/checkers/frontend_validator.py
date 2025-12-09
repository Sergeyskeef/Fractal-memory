"""
Frontend validator for checking React/TypeScript integration with backend.

Checks:
- TypeScript types match FastAPI models
- CORS configuration
- Error handling in React components
- API endpoint usage
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from ..core.base_checker import StaticChecker
from ..core.models import Issue, Category, Severity
from ..config import AuditConfig


class FrontendValidator(StaticChecker):
    """Проверка интеграции React frontend с FastAPI backend."""
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="FrontendValidator", timeout_seconds=config.default_timeout_seconds)
        self.config = config
        self.frontend_dir = config.project_root / "fractal-memory-interface"
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки frontend."""
        issues = []
        
        # Check if frontend directory exists
        if not self.frontend_dir.exists():
            issues.append(self.create_issue(
                category=Category.FRONTEND,
                severity=Severity.HIGH,
                title="Frontend directory not found",
                description=f"Expected frontend at {self.frontend_dir}",
                location=str(self.config.project_root),
                impact="Cannot validate frontend integration",
                recommendation="Ensure frontend is in fractal-memory-interface/",
            ))
            return issues
        
        # Check API types
        self.logger.info("Checking API types...")
        issues.extend(await self.check_api_types())
        
        # Check CORS config
        self.logger.info("Checking CORS configuration...")
        issues.extend(await self.check_cors_config())
        
        # Check error handling
        self.logger.info("Checking error handling...")
        issues.extend(await self.check_error_handling())
        
        # Check API endpoint usage
        self.logger.info("Checking API endpoint usage...")
        issues.extend(await self.check_api_usage())
        
        return issues
    
    async def check_api_types(self) -> List[Issue]:
        """
        Проверить соответствие TypeScript типов и FastAPI моделей.
        
        Validates: Requirements 10.1
        """
        issues = []
        
        try:
            # Find TypeScript type definitions
            types_file = self.frontend_dir / "types.ts"
            
            if not types_file.exists():
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.HIGH,
                    title="TypeScript types file not found",
                    description=f"Expected types.ts at {types_file}",
                    location=str(self.frontend_dir),
                    impact="No type definitions for API responses",
                    recommendation="Create types.ts with API type definitions",
                ))
                return issues
            
            # Parse TypeScript types
            ts_types = self._parse_typescript_types(types_file)
            
            # Find FastAPI models
            backend_models = self._find_fastapi_models()
            
            # Compare types
            for model_name, model_fields in backend_models.items():
                if model_name not in ts_types:
                    issues.append(self.create_issue(
                        category=Category.FRONTEND,
                        severity=Severity.MEDIUM,
                        title=f"Missing TypeScript type for {model_name}",
                        description=f"Backend model '{model_name}' has no corresponding TypeScript type",
                        location=str(types_file),
                        impact="Frontend may use incorrect types for API responses",
                        recommendation=f"Add TypeScript interface for {model_name}",
                    ))
                else:
                    # Check field compatibility
                    ts_fields = ts_types[model_name]
                    
                    # Check for missing fields in TypeScript
                    missing_in_ts = set(model_fields.keys()) - set(ts_fields.keys())
                    if missing_in_ts:
                        issues.append(self.create_issue(
                            category=Category.FRONTEND,
                            severity=Severity.MEDIUM,
                            title=f"TypeScript type {model_name} missing fields",
                            description=f"Missing fields: {', '.join(missing_in_ts)}",
                            location=str(types_file),
                            impact="Frontend may not handle all API response fields",
                            recommendation=f"Add missing fields to {model_name} interface",
                        ))
                    
                    # Check for extra fields in TypeScript
                    extra_in_ts = set(ts_fields.keys()) - set(model_fields.keys())
                    if extra_in_ts:
                        issues.append(self.create_issue(
                            category=Category.FRONTEND,
                            severity=Severity.LOW,
                            title=f"TypeScript type {model_name} has extra fields",
                            description=f"Extra fields: {', '.join(extra_in_ts)}",
                            location=str(types_file),
                            impact="Frontend expects fields not in API response",
                            recommendation=f"Remove extra fields or add them to backend model",
                        ))
        
        except Exception as e:
            self.logger.error(f"Error checking API types: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.FRONTEND,
                severity=Severity.MEDIUM,
                title="Failed to check API types",
                description=f"Error: {str(e)}",
                location="FrontendValidator",
                impact="Cannot validate type compatibility",
                recommendation="Check TypeScript and Python files are accessible",
            ))
        
        return issues
    
    async def check_cors_config(self) -> List[Issue]:
        """
        Проверить конфигурацию CORS.
        
        Validates: Requirements 10.4
        """
        issues = []
        
        try:
            # Check backend CORS configuration
            backend_main = self.config.backend_dir / "main.py"
            
            if not backend_main.exists():
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.HIGH,
                    title="Backend main.py not found",
                    description=f"Expected main.py at {backend_main}",
                    location=str(self.config.backend_dir),
                    impact="Cannot validate CORS configuration",
                    recommendation="Ensure backend/main.py exists",
                ))
                return issues
            
            with open(backend_main, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for CORS middleware
            if 'CORSMiddleware' not in content:
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.CRITICAL,
                    title="CORS middleware not configured",
                    description="CORSMiddleware not found in backend/main.py",
                    location=str(backend_main),
                    impact="Frontend cannot make requests to backend",
                    recommendation="Add CORSMiddleware to FastAPI app",
                ))
            else:
                # Check CORS configuration
                if 'allow_origins' not in content:
                    issues.append(self.create_issue(
                        category=Category.FRONTEND,
                        severity=Severity.HIGH,
                        title="CORS allow_origins not configured",
                        description="allow_origins parameter not found in CORS config",
                        location=str(backend_main),
                        impact="CORS may not allow frontend origin",
                        recommendation="Configure allow_origins in CORSMiddleware",
                    ))
                
                if 'allow_credentials' not in content:
                    issues.append(self.create_issue(
                        category=Category.FRONTEND,
                        severity=Severity.LOW,
                        title="CORS allow_credentials not configured",
                        description="allow_credentials parameter not found in CORS config",
                        location=str(backend_main),
                        impact="Credentials may not be sent with requests",
                        recommendation="Set allow_credentials=True if needed",
                    ))
            
            # Check frontend API URL configuration
            constants_file = self.frontend_dir / "constants.ts"
            env_file = self.frontend_dir / ".env.local"
            
            has_api_url = False
            
            if constants_file.exists():
                with open(constants_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'API_URL' in content or 'VITE_API_URL' in content:
                        has_api_url = True
            
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'API_URL' in content or 'VITE_API_URL' in content:
                        has_api_url = True
            
            if not has_api_url:
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.MEDIUM,
                    title="API URL not configured in frontend",
                    description="No API_URL or VITE_API_URL found in constants.ts or .env.local",
                    location=str(self.frontend_dir),
                    impact="Frontend may use incorrect API endpoint",
                    recommendation="Configure API URL in constants.ts or .env.local",
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking CORS config: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.FRONTEND,
                severity=Severity.MEDIUM,
                title="Failed to check CORS configuration",
                description=f"Error: {str(e)}",
                location="FrontendValidator",
                impact="Cannot validate CORS setup",
                recommendation="Check backend and frontend files are accessible",
            ))
        
        return issues
    
    async def check_error_handling(self) -> List[Issue]:
        """
        Проверить обработку ошибок в React компонентах.
        
        Validates: Requirements 10.5
        """
        issues = []
        
        try:
            # Find React component files
            components_dir = self.frontend_dir / "components"
            
            if not components_dir.exists():
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.MEDIUM,
                    title="Components directory not found",
                    description=f"Expected components at {components_dir}",
                    location=str(self.frontend_dir),
                    impact="Cannot validate component error handling",
                    recommendation="Ensure components are in components/",
                ))
                return issues
            
            # Check each component file
            component_files = list(components_dir.glob('**/*.tsx')) + list(components_dir.glob('**/*.ts'))
            
            for component_file in component_files:
                file_issues = await self._check_component_error_handling(component_file)
                issues.extend(file_issues)
            
            # Check API service file
            services_dir = self.frontend_dir / "services"
            if services_dir.exists():
                api_file = services_dir / "api.ts"
                if api_file.exists():
                    api_issues = await self._check_api_service_error_handling(api_file)
                    issues.extend(api_issues)
        
        except Exception as e:
            self.logger.error(f"Error checking error handling: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.FRONTEND,
                severity=Severity.MEDIUM,
                title="Failed to check error handling",
                description=f"Error: {str(e)}",
                location="FrontendValidator",
                impact="Cannot validate error handling",
                recommendation="Check component files are accessible",
            ))
        
        return issues
    
    async def check_api_usage(self) -> List[Issue]:
        """
        Проверить использование API endpoints в frontend.
        
        Validates: Requirements 10.1, 10.2, 10.3
        """
        issues = []
        
        try:
            # Find API service file
            services_dir = self.frontend_dir / "services"
            api_file = services_dir / "api.ts" if services_dir.exists() else None
            
            if not api_file or not api_file.exists():
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.MEDIUM,
                    title="API service file not found",
                    description=f"Expected api.ts in services/",
                    location=str(self.frontend_dir),
                    impact="API calls may not be centralized",
                    recommendation="Create services/api.ts for API calls",
                ))
                return issues
            
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required endpoints
            required_endpoints = {
                '/chat': 'Chat endpoint',
                '/memory/stats': 'Memory stats endpoint',
                '/memory': 'Memory retrieval endpoint',
            }
            
            for endpoint, description in required_endpoints.items():
                if endpoint not in content:
                    issues.append(self.create_issue(
                        category=Category.FRONTEND,
                        severity=Severity.MEDIUM,
                        title=f"API endpoint not used: {endpoint}",
                        description=f"{description} not found in API service",
                        location=str(api_file),
                        impact=f"Frontend may not use {description.lower()}",
                        recommendation=f"Add API call for {endpoint}",
                    ))
            
            # Check for error handling in API calls
            if 'catch' not in content and 'try' not in content:
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.HIGH,
                    title="No error handling in API service",
                    description="API service doesn't use try/catch for error handling",
                    location=str(api_file),
                    impact="API errors may crash the application",
                    recommendation="Add try/catch blocks to all API calls",
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking API usage: {e}", exc_info=True)
            issues.append(self.create_issue(
                category=Category.FRONTEND,
                severity=Severity.MEDIUM,
                title="Failed to check API usage",
                description=f"Error: {str(e)}",
                location="FrontendValidator",
                impact="Cannot validate API usage",
                recommendation="Check API service file is accessible",
            ))
        
        return issues
    
    async def _check_component_error_handling(self, component_file: Path) -> List[Issue]:
        """Проверить обработку ошибок в компоненте."""
        issues = []
        
        try:
            with open(component_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if component makes API calls
            has_api_calls = 'fetch(' in content or 'axios' in content or 'api.' in content
            
            if has_api_calls:
                # Check for error handling
                has_try_catch = 'try' in content and 'catch' in content
                has_error_state = 'error' in content.lower() or 'Error' in content
                
                if not has_try_catch and not has_error_state:
                    issues.append(self.create_issue(
                        category=Category.FRONTEND,
                        severity=Severity.MEDIUM,
                        title=f"Component missing error handling: {component_file.name}",
                        description="Component makes API calls but doesn't handle errors",
                        location=str(component_file),
                        impact="Errors may not be displayed to user",
                        recommendation="Add try/catch and error state to component",
                    ))
        
        except Exception as e:
            self.logger.warning(f"Error checking component {component_file}: {e}")
        
        return issues
    
    async def _check_api_service_error_handling(self, api_file: Path) -> List[Issue]:
        """Проверить обработку ошибок в API сервисе."""
        issues = []
        
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for proper error handling
            if 'throw' not in content and 'reject' not in content:
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.MEDIUM,
                    title="API service doesn't propagate errors",
                    description="API service should throw or reject on errors",
                    location=str(api_file),
                    impact="Components may not know when API calls fail",
                    recommendation="Throw errors or reject promises on API failures",
                ))
            
            # Check for response validation
            if 'response.ok' not in content and 'status' not in content:
                issues.append(self.create_issue(
                    category=Category.FRONTEND,
                    severity=Severity.MEDIUM,
                    title="API service doesn't validate responses",
                    description="API service should check response.ok or status",
                    location=str(api_file),
                    impact="Failed requests may be treated as successful",
                    recommendation="Check response.ok before parsing JSON",
                ))
        
        except Exception as e:
            self.logger.warning(f"Error checking API service {api_file}: {e}")
        
        return issues
    
    def _parse_typescript_types(self, types_file: Path) -> Dict[str, Dict[str, str]]:
        """
        Парсинг TypeScript типов из файла.
        
        Returns:
            Dict[type_name, Dict[field_name, field_type]]
        """
        types = {}
        
        try:
            with open(types_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex-based parsing for interfaces
            # Pattern: interface TypeName { field: type; ... }
            interface_pattern = r'interface\s+(\w+)\s*\{([^}]+)\}'
            
            for match in re.finditer(interface_pattern, content):
                type_name = match.group(1)
                fields_str = match.group(2)
                
                fields = {}
                # Parse fields: field: type;
                field_pattern = r'(\w+)\s*:\s*([^;]+);'
                
                for field_match in re.finditer(field_pattern, fields_str):
                    field_name = field_match.group(1)
                    field_type = field_match.group(2).strip()
                    fields[field_name] = field_type
                
                types[type_name] = fields
            
            # Also check for type aliases
            # Pattern: type TypeName = { field: type; ... }
            type_pattern = r'type\s+(\w+)\s*=\s*\{([^}]+)\}'
            
            for match in re.finditer(type_pattern, content):
                type_name = match.group(1)
                fields_str = match.group(2)
                
                fields = {}
                field_pattern = r'(\w+)\s*:\s*([^;]+);'
                
                for field_match in re.finditer(field_pattern, fields_str):
                    field_name = field_match.group(1)
                    field_type = field_match.group(2).strip()
                    fields[field_name] = field_type
                
                types[type_name] = fields
        
        except Exception as e:
            self.logger.warning(f"Error parsing TypeScript types: {e}")
        
        return types
    
    def _find_fastapi_models(self) -> Dict[str, Dict[str, str]]:
        """
        Найти Pydantic модели в backend.
        
        Returns:
            Dict[model_name, Dict[field_name, field_type]]
        """
        models = {}
        
        try:
            # Find all Python files in backend
            backend_files = list(self.config.backend_dir.glob('**/*.py'))
            
            for file_path in backend_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content, filename=str(file_path))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if it's a Pydantic model
                            is_pydantic = False
                            for base in node.bases:
                                if isinstance(base, ast.Name) and base.id == 'BaseModel':
                                    is_pydantic = True
                                    break
                            
                            if is_pydantic:
                                fields = {}
                                for item in node.body:
                                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                        field_name = item.target.id
                                        field_type = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else 'unknown'
                                        fields[field_name] = field_type
                                
                                models[node.name] = fields
                
                except Exception:
                    continue
        
        except Exception as e:
            self.logger.warning(f"Error finding FastAPI models: {e}")
        
        return models
