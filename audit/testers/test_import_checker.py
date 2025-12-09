"""
Property-based tests for ImportChecker.

Property 1: Import completeness
- For any valid Python/TypeScript file, all imports should be validated
- Invalid imports should be detected
"""

import tempfile
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st, settings, assume

from ..checkers.import_checker import ImportChecker
from ..config import AuditConfig
from ..core.models import Category, Severity


# === Strategies for generating test data ===

@st.composite
def python_import_statement(draw):
    """Generate a Python import statement."""
    import_type = draw(st.sampled_from(['import', 'from']))
    
    if import_type == 'import':
        # import module
        module = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        return f"import {module}"
    else:
        # from module import name
        module = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        return f"from {module} import {name}"


@st.composite
def python_file_with_imports(draw):
    """Generate a Python file with imports."""
    num_imports = draw(st.integers(min_value=0, max_value=10))
    imports = [draw(python_import_statement()) for _ in range(num_imports)]
    
    # Add some code
    code = draw(st.text(
        alphabet=st.characters(blacklist_characters='\x00'),
        min_size=0,
        max_size=100
    ))
    
    return '\n'.join(imports + ['', code])


@st.composite
def typescript_import_statement(draw):
    """Generate a TypeScript import statement."""
    import_type = draw(st.sampled_from(['named', 'default', 'namespace', 'side-effect']))
    
    module = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=20
    ))
    
    if import_type == 'named':
        # import { X } from 'module'
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        return f"import {{ {name} }} from '{module}';"
    elif import_type == 'default':
        # import X from 'module'
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        return f"import {name} from '{module}';"
    elif import_type == 'namespace':
        # import * as X from 'module'
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=20
        ))
        return f"import * as {name} from '{module}';"
    else:
        # import 'module'
        return f"import '{module}';"


# === Property Tests ===

class TestImportCheckerProperties:
    """Property-based tests for ImportChecker."""
    
    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config for testing."""
        config = AuditConfig()
        config.project_root = tmp_path
        config.src_dir = tmp_path / "src"
        config.backend_dir = tmp_path / "backend"
        config.frontend_dir = tmp_path / "frontend"
        
        # Create directories
        config.src_dir.mkdir(exist_ok=True)
        config.backend_dir.mkdir(exist_ok=True)
        config.frontend_dir.mkdir(exist_ok=True)
        
        return config
    
    @pytest.mark.asyncio
    @given(content=python_file_with_imports())
    @settings(max_examples=50, deadline=None)
    async def test_property_python_import_validation(self, temp_config, content):
        """
        Property 1: Import completeness for Python files.
        
        For any Python file, the checker should:
        1. Parse the file without crashing
        2. Return a list of issues (possibly empty)
        3. All issues should have valid structure
        """
        # Create temporary file
        test_file = temp_config.src_dir / "test_module.py"
        
        try:
            test_file.write_text(content)
        except Exception:
            # Skip invalid content
            assume(False)
        
        # Run checker
        checker = ImportChecker(temp_config)
        
        try:
            issues = await checker.check_python_imports(test_file)
            
            # Property: Should return a list
            assert isinstance(issues, list)
            
            # Property: All issues should have valid structure
            for issue in issues:
                assert hasattr(issue, 'category')
                assert hasattr(issue, 'severity')
                assert hasattr(issue, 'title')
                assert hasattr(issue, 'description')
                assert hasattr(issue, 'location')
                assert hasattr(issue, 'impact')
                assert hasattr(issue, 'recommendation')
                
                # Property: Category should be IMPORTS
                assert issue.category == Category.IMPORTS
                
                # Property: Severity should be valid
                assert issue.severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
        
        except Exception as e:
            # If file has syntax errors, checker should handle gracefully
            # and return issues about syntax errors
            pytest.fail(f"Checker crashed on valid input: {e}")
    
    @pytest.mark.asyncio
    @given(imports=st.lists(typescript_import_statement(), min_size=0, max_size=10))
    @settings(max_examples=50, deadline=None)
    async def test_property_typescript_import_validation(self, temp_config, imports):
        """
        Property 1: Import completeness for TypeScript files.
        
        For any TypeScript file, the checker should:
        1. Parse the file without crashing
        2. Return a list of issues (possibly empty)
        3. All issues should have valid structure
        """
        # Create temporary file
        test_file = temp_config.frontend_dir / "test_component.tsx"
        content = '\n'.join(imports)
        
        try:
            test_file.write_text(content)
        except Exception:
            # Skip invalid content
            assume(False)
        
        # Run checker
        checker = ImportChecker(temp_config)
        
        try:
            issues = await checker.check_typescript_imports(test_file)
            
            # Property: Should return a list
            assert isinstance(issues, list)
            
            # Property: All issues should have valid structure
            for issue in issues:
                assert hasattr(issue, 'category')
                assert hasattr(issue, 'severity')
                assert issue.category == Category.IMPORTS
        
        except Exception as e:
            pytest.fail(f"Checker crashed on valid input: {e}")
    
    @pytest.mark.asyncio
    async def test_property_missing_import_detected(self, temp_config):
        """
        Property: Missing imports should be detected.
        
        If a file imports a non-existent local module, it should be flagged.
        """
        # Create a file with a bad import
        test_file = temp_config.src_dir / "test_bad_import.py"
        test_file.write_text("from src.nonexistent_module import something\n")
        
        checker = ImportChecker(temp_config)
        issues = await checker.check_python_imports(test_file)
        
        # Property: Should detect the missing module
        assert len(issues) > 0
        assert any('nonexistent_module' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_valid_import_not_flagged(self, temp_config):
        """
        Property: Valid imports should not be flagged.
        
        If a file imports an existing module, it should not be flagged.
        """
        # Create a valid module
        module_file = temp_config.src_dir / "valid_module.py"
        module_file.write_text("def hello(): pass\n")
        
        # Create a file that imports it
        test_file = temp_config.src_dir / "test_valid_import.py"
        test_file.write_text("from src.valid_module import hello\n")
        
        checker = ImportChecker(temp_config)
        issues = await checker.check_python_imports(test_file)
        
        # Property: Should not flag valid imports
        # (Note: This might still flag if the module isn't in sys.path, 
        # but it shouldn't flag for missing file)
        assert all('valid_module' not in issue.description or 'not found' not in issue.description 
                   for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_circular_dependency_detected(self, temp_config):
        """
        Property: Circular dependencies should be detected.
        
        If module A imports B and B imports A, it should be flagged.
        """
        # Create module A
        module_a = temp_config.src_dir / "module_a.py"
        module_a.write_text("from src.module_b import func_b\n")
        
        # Create module B
        module_b = temp_config.src_dir / "module_b.py"
        module_b.write_text("from src.module_a import func_a\n")
        
        checker = ImportChecker(temp_config)
        
        # Check both files to build dependency graph
        await checker.check_python_imports(module_a)
        await checker.check_python_imports(module_b)
        
        # Find circular dependencies
        issues = await checker.find_circular_dependencies()
        
        # Property: Should detect the circular dependency
        assert len(issues) > 0
        assert any('circular' in issue.title.lower() for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_stdlib_imports_not_flagged(self, temp_config):
        """
        Property: Standard library imports should not be flagged.
        
        Imports from Python stdlib should not be flagged as missing.
        """
        # Create a file with stdlib imports
        test_file = temp_config.src_dir / "test_stdlib.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
from typing import List, Dict
import asyncio
""")
        
        checker = ImportChecker(temp_config)
        issues = await checker.check_python_imports(test_file)
        
        # Property: Should not flag stdlib imports
        stdlib_modules = ['os', 'sys', 'pathlib', 'typing', 'asyncio']
        for module in stdlib_modules:
            assert not any(
                module in issue.description and 'not found' in issue.description 
                for issue in issues
            ), f"Stdlib module {module} was incorrectly flagged"
    
    @pytest.mark.asyncio
    async def test_property_relative_import_resolution(self, temp_config):
        """
        Property: Relative imports should be resolved correctly.
        
        Relative imports like "from . import X" should be resolved to absolute paths.
        """
        # Create package structure
        package_dir = temp_config.src_dir / "mypackage"
        package_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        (package_dir / "__init__.py").write_text("")
        
        # Create module_a.py
        (package_dir / "module_a.py").write_text("def func_a(): pass\n")
        
        # Create module_b.py with relative import
        test_file = package_dir / "module_b.py"
        test_file.write_text("from . import module_a\n")
        
        checker = ImportChecker(temp_config)
        issues = await checker.check_python_imports(test_file)
        
        # Property: Should resolve relative import correctly
        # (Should not flag as missing since module_a exists)
        assert not any(
            'module_a' in issue.description and 'not found' in issue.description 
            for issue in issues
        )


# === Integration Tests ===

class TestImportCheckerIntegration:
    """Integration tests with real project structure."""
    
    @pytest.mark.asyncio
    async def test_check_real_project_imports(self):
        """Test checking imports in the real project."""
        config = AuditConfig()
        checker = ImportChecker(config)
        
        # Run full check
        issues = await checker._check()
        
        # Should complete without crashing
        assert isinstance(issues, list)
        
        # Log results for inspection
        print(f"\nFound {len(issues)} import issues:")
        for issue in issues[:10]:  # Print first 10
            print(f"  - [{issue.severity.value}] {issue.title}")
            print(f"    Location: {issue.location}")
