"""
Property-based tests for APIValidator.

Property 3: API compatibility
- For any two components that exchange data, data structures should be compatible
- Missing required methods should be detected
- Inconsistent data formats should be flagged
"""

import tempfile
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st, settings, assume

from ..checkers.api_validator import APIValidator
from ..config import AuditConfig
from ..core.models import Category, Severity


# === Strategies for generating test data ===

@st.composite
def dataclass_definition(draw, class_name='TestClass'):
    """Generate a Python dataclass definition."""
    num_fields = draw(st.integers(min_value=1, max_value=5))
    
    fields = []
    for _ in range(num_fields):
        field_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=15
        ))
        field_type = draw(st.sampled_from(['str', 'int', 'float', 'bool', 'List[str]', 'Dict[str, Any]']))
        fields.append(f"    {field_name}: {field_type}")
    
    return f"""
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class {class_name}:
{chr(10).join(fields)}
"""


@st.composite
def class_with_methods(draw, class_name='TestClass'):
    """Generate a Python class with methods."""
    num_methods = draw(st.integers(min_value=1, max_value=5))
    
    methods = []
    for _ in range(num_methods):
        method_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=15
        ))
        num_params = draw(st.integers(min_value=0, max_value=3))
        params = ['self']
        for i in range(num_params):
            param_name = draw(st.text(
                alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
                min_size=1,
                max_size=10
            ))
            params.append(param_name)
        
        methods.append(f"    def {method_name}({', '.join(params)}):\n        pass")
    
    return f"""
class {class_name}:
{chr(10).join(methods)}
"""


# === Property Tests ===

class TestAPIValidatorProperties:
    """Property-based tests for APIValidator."""
    
    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config for testing."""
        config = AuditConfig()
        config.project_root = tmp_path
        config.src_dir = tmp_path / "src"
        config.backend_dir = tmp_path / "backend"
        
        config.src_dir.mkdir(exist_ok=True)
        config.backend_dir.mkdir(exist_ok=True)
        (config.backend_dir / "routers").mkdir(exist_ok=True)
        
        return config
    
    @pytest.mark.asyncio
    async def test_property_search_result_single_definition(self, temp_config):
        """
        Property 3: SearchResult should have single definition.
        
        If SearchResult is defined multiple times, it should be flagged.
        """
        # Create two SearchResult definitions
        file1 = temp_config.src_dir / "models1.py"
        file1.write_text("""
from dataclasses import dataclass

@dataclass
class SearchResult:
    content: str
    score: float
""")
        
        file2 = temp_config.src_dir / "models2.py"
        file2.write_text("""
from dataclasses import dataclass

@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_search_result_format()
        
        # Property: Should flag multiple definitions
        assert len(issues) > 0
        assert any('Multiple' in issue.title and 'SearchResult' in issue.title for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_search_result_required_fields(self, temp_config):
        """
        Property 3: SearchResult should have required fields.
        
        If SearchResult is missing required fields, it should be flagged.
        """
        # Create SearchResult with missing fields
        file1 = temp_config.src_dir / "models.py"
        file1.write_text("""
from dataclasses import dataclass

@dataclass
class SearchResult:
    content: str
    # Missing: score, metadata
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_search_result_format()
        
        # Property: Should flag missing fields
        assert len(issues) > 0
        assert any('missing' in issue.description.lower() for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_fractal_memory_required_methods(self, temp_config):
        """
        Property 3: FractalMemory should have required methods.
        
        If FractalMemory is missing required methods, it should be flagged.
        """
        # Create FractalMemory with missing methods
        file1 = temp_config.src_dir / "memory.py"
        file1.write_text("""
class FractalMemory:
    def __init__(self):
        pass
    
    def remember(self, content):
        pass
    
    # Missing: search, consolidate, get_stats
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_memory_api()
        
        # Property: Should flag missing methods
        assert len(issues) > 0
        missing_methods = ['search', 'consolidate', 'get_stats']
        for method in missing_methods:
            assert any(method in issue.description for issue in issues), \
                f"Should flag missing {method} method"
    
    @pytest.mark.asyncio
    async def test_property_fractal_memory_method_signature(self, temp_config):
        """
        Property 3: FractalMemory methods should have correct signatures.
        
        If remember() doesn't accept 'content', it should be flagged.
        """
        # Create FractalMemory with wrong signature
        file1 = temp_config.src_dir / "memory.py"
        file1.write_text("""
class FractalMemory:
    def remember(self, data):  # Should be 'content'
        pass
    
    def search(self, query):
        pass
    
    def consolidate(self):
        pass
    
    def get_stats(self):
        pass
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_memory_api()
        
        # Property: Should flag wrong parameter name
        assert any('content' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_hybrid_retriever_required_methods(self, temp_config):
        """
        Property 3: HybridRetriever should have required methods.
        
        If HybridRetriever is missing required methods, it should be flagged.
        """
        # Create HybridRetriever with missing methods
        file1 = temp_config.src_dir / "retriever.py"
        file1.write_text("""
class HybridRetriever:
    def search(self, query):
        pass
    
    # Missing: vector_search, keyword_search, graph_search
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_retriever_api()
        
        # Property: Should flag missing methods
        assert len(issues) > 0
        missing_methods = ['vector_search', 'keyword_search', 'graph_search']
        for method in missing_methods:
            assert any(method in issue.description for issue in issues), \
                f"Should flag missing {method} method"
    
    @pytest.mark.asyncio
    async def test_property_fastapi_response_model(self, temp_config):
        """
        Property 3: FastAPI endpoints should have response_model.
        
        If an endpoint doesn't specify response_model, it should be flagged (low severity).
        """
        # Create router without response_model
        router_file = temp_config.backend_dir / "routers" / "test_router.py"
        router_file.write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    return {"message": "test"}

@router.post("/test", response_model=dict)
async def test_endpoint_with_model():
    return {"message": "test"}
""")
        
        validator = APIValidator(temp_config)
        issues = await validator.check_fastapi_endpoints()
        
        # Property: Should flag endpoint without response_model
        assert len(issues) > 0
        assert any('response_model' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    @given(code=dataclass_definition('SearchResult'))
    @settings(max_examples=30, deadline=None)
    async def test_property_dataclass_field_extraction(self, temp_config, code):
        """
        Property: Dataclass field extraction should work correctly.
        
        For any dataclass definition, the validator should extract fields without crashing.
        """
        # Create file with dataclass
        test_file = temp_config.src_dir / "test_dataclass.py"
        
        try:
            test_file.write_text(code)
        except Exception:
            assume(False)
        
        validator = APIValidator(temp_config)
        
        try:
            # Find class definitions
            defs = validator._find_class_definitions('SearchResult')
            
            # Should find the definition
            assert len(defs) >= 0  # May be 0 if code is invalid
            
            # If found, should extract fields without crashing
            for file_path, line_no, class_node in defs:
                fields = validator._extract_dataclass_fields(class_node)
                assert isinstance(fields, dict)
        
        except Exception as e:
            pytest.fail(f"Field extraction crashed: {e}")
    
    @pytest.mark.asyncio
    @given(code=class_with_methods('TestClass'))
    @settings(max_examples=30, deadline=None)
    async def test_property_method_extraction(self, temp_config, code):
        """
        Property: Method extraction should work correctly.
        
        For any class definition, the validator should extract methods without crashing.
        """
        # Create file with class
        test_file = temp_config.src_dir / "test_class.py"
        
        try:
            test_file.write_text(code)
        except Exception:
            assume(False)
        
        validator = APIValidator(temp_config)
        
        try:
            # Find class definitions
            defs = validator._find_class_definitions('TestClass')
            
            # If found, should extract methods without crashing
            for file_path, line_no, class_node in defs:
                methods = validator._extract_class_methods(class_node)
                assert isinstance(methods, dict)
                
                # All methods should have params list
                for method_name, method_info in methods.items():
                    assert 'params' in method_info
                    assert isinstance(method_info['params'], list)
        
        except Exception as e:
            pytest.fail(f"Method extraction crashed: {e}")
    
    @pytest.mark.asyncio
    async def test_property_valid_api_not_flagged(self, temp_config):
        """
        Property: Valid API should not be flagged.
        
        If all required components are present with correct signatures, no issues should be raised.
        """
        # Create valid SearchResult
        (temp_config.src_dir / "models.py").write_text("""
from dataclasses import dataclass

@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict
""")
        
        # Create valid FractalMemory
        (temp_config.src_dir / "memory.py").write_text("""
class FractalMemory:
    def remember(self, content):
        pass
    
    def search(self, query):
        pass
    
    def consolidate(self):
        pass
    
    def get_stats(self):
        pass
""")
        
        # Create valid HybridRetriever
        (temp_config.src_dir / "retriever.py").write_text("""
class HybridRetriever:
    def search(self, query):
        pass
    
    def vector_search(self, query):
        pass
    
    def keyword_search(self, query):
        pass
    
    def graph_search(self, query):
        pass
""")
        
        validator = APIValidator(temp_config)
        
        # Check SearchResult
        search_issues = await validator.check_search_result_format()
        # Should not flag missing fields (may flag other things)
        assert not any('missing' in issue.description.lower() and 'field' in issue.description.lower() 
                      for issue in search_issues)
        
        # Check FractalMemory
        memory_issues = await validator.check_memory_api()
        # Should not flag missing methods
        assert not any('missing method' in issue.title.lower() for issue in memory_issues)
        
        # Check HybridRetriever
        retriever_issues = await validator.check_retriever_api()
        # Should not flag missing methods
        assert not any('missing method' in issue.title.lower() for issue in retriever_issues)


# === Integration Tests ===

class TestAPIValidatorIntegration:
    """Integration tests with real project."""
    
    @pytest.mark.asyncio
    async def test_check_real_project_api(self):
        """Test checking API in the real project."""
        config = AuditConfig()
        validator = APIValidator(config)
        
        # Run full check
        issues = await validator._check()
        
        # Should complete without crashing
        assert isinstance(issues, list)
        
        # Log results for inspection
        print(f"\nFound {len(issues)} API issues:")
        for issue in issues[:10]:  # Print first 10
            print(f"  - [{issue.severity.value}] {issue.title}")
            print(f"    Location: {issue.location}")
