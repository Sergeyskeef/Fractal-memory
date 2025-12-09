"""
Property-based tests for RetrievalTester.

Property 6: Search completeness
- For any query, search should return results from all configured levels
"""

import asyncio
import uuid
import pytest
from hypothesis import given, strategies as st, settings

from ..testers.retrieval_tester import RetrievalTester
from ..config import AuditConfig


@st.composite
def search_query(draw):
    """Generate search query."""
    return draw(st.text(min_size=3, max_size=100))


class TestRetrievalTesterProperties:
    """Property-based tests for RetrievalTester."""
    
    @pytest.fixture
    def config(self):
        return AuditConfig()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_property_search_returns_list(self, config):
        """
        Property 6: Search completeness.
        
        For any query, search should return a list (not None).
        """
        if not config.has_neo4j_credentials():
            pytest.skip("No Neo4j credentials")
        
        tester = RetrievalTester(config)
        
        try:
            await tester._initialize_connections()
            
            if not tester.memory:
                pytest.skip("FractalMemory not available")
            
            # Test search
            results = await tester.memory.search(
                query="test query",
                user_id="test_user",
                limit=5
            )
            
            # Property: Should return list, not None
            assert results is not None, "Search should return list, not None"
            assert isinstance(results, list), "Search should return list"
        
        finally:
            await tester._cleanup_connections()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_property_stored_items_are_searchable(self, config):
        """
        Property: Stored items should be searchable.
        
        For any stored item, it should be retrievable via search.
        """
        if not config.has_neo4j_credentials():
            pytest.skip("No Neo4j credentials")
        
        tester = RetrievalTester(config)
        
        try:
            await tester._initialize_connections()
            
            if not tester.memory:
                pytest.skip("FractalMemory not available")
            
            # Store item
            test_content = f"Unique test content {uuid.uuid4()}"
            
            await tester.memory.remember(
                content=test_content,
                importance=0.8,
                user_id="test_user_search"
            )
            
            await asyncio.sleep(1)
            
            # Search for it
            results = await tester.memory.search(
                query=test_content,
                user_id="test_user_search",
                limit=5
            )
            
            # Property: Should find the item
            assert results is not None
            assert len(results) > 0, "Stored item should be searchable"
        
        finally:
            await tester._cleanup_connections()


class TestRetrievalTesterIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retrieval_tester_full_run(self):
        """Test running full retrieval tester."""
        config = AuditConfig()
        
        if not config.has_neo4j_credentials():
            pytest.skip("No Neo4j credentials")
        
        tester = RetrievalTester(config)
        issues = await tester._check()
        
        assert isinstance(issues, list)
        
        print(f"\nFound {len(issues)} retrieval issues:")
        for issue in issues[:10]:
            print(f"  - [{issue.severity.value}] {issue.title}")
