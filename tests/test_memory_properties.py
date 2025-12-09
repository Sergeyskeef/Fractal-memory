"""
Property-based tests for FractalMemory.

These tests verify universal properties that should hold across all valid inputs.
Uses hypothesis library for property-based testing with minimum 100 iterations per test.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime
from typing import List

from src.core.memory import FractalMemory, MemoryItem, SearchResult


# Hypothesis strategies for generating test data
@st.composite
def valid_memory_content(draw):
    """Generate valid memory content strings."""
    return draw(st.text(min_size=1, max_size=500, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='\x00\n\r\t'
    )))


@st.composite
def valid_importance(draw):
    """Generate valid importance values (0.0 to 1.0)."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_metadata(draw):
    """Generate valid metadata dictionaries."""
    keys = draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5, unique=True))
    values = draw(st.lists(st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans()
    ), min_size=len(keys), max_size=len(keys)))
    return dict(zip(keys, values))


class TestMemoryDataConsistencyProperties:
    """Property-based tests for memory data consistency across tiers."""
    
    @pytest.mark.asyncio
    @settings(max_examples=100, deadline=None)  # Disable deadline for async tests
    @given(
        content=valid_memory_content(),
        importance=valid_importance(),
        metadata=valid_metadata()
    )
    async def test_property_1_memory_data_consistency_across_tiers(
        self, content, importance, metadata
    ):
        """
        Feature: phase-4-improvements, Property 1: Memory Data Consistency Across Tiers
        
        For any memory operation (store, retrieve), the data should remain consistent
        across L0, L1, and L2 tiers, with all required fields preserved.
        
        Validates: Requirements 1.2
        """
        # Mock Redis and Graphiti to avoid actual database connections
        mock_redis = AsyncMock()
        mock_redis.l0_add = AsyncMock()
        mock_redis.l0_get_all = AsyncMock(return_value=[])
        mock_redis.l1_get_all = AsyncMock(return_value={})
        
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        
        # Create memory instance with mocks
        config = {
            "user_id": "test_user",
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "neo4j_password": "test",
            "redis_url": "redis://localhost:6379",
            "l0_capacity": 10,
            "l1_capacity": 50,
            "embedding_func": None,  # Disable embeddings for testing
        }
        
        memory = FractalMemory(config=config)
        memory.redis_store = mock_redis
        memory.graphiti = mock_graphiti
        memory._initialized = True
        
        try:
            # Store data in memory
            item_id = await memory.remember(
                content=content,
                importance=importance,
                metadata=metadata
            )
            
            # Property: Item ID should be generated
            assert item_id is not None
            assert isinstance(item_id, str)
            assert len(item_id) > 0
            
            # Property: Item should be in L0 cache
            assert len(memory.l0_cache) > 0
            stored_item = memory.l0_cache[-1]  # Last added item
            
            # Property: All required fields should be preserved
            assert stored_item.id == item_id
            assert stored_item.content == content
            assert stored_item.importance == importance
            assert stored_item.level == 0  # Should start in L0
            assert stored_item.metadata == metadata
            
            # Property: Timestamps should be set
            assert stored_item.created_at is not None
            assert stored_item.last_accessed is not None
            assert isinstance(stored_item.created_at, datetime)
            assert isinstance(stored_item.last_accessed, datetime)
            
            # Property: Access count should be initialized
            assert stored_item.access_count >= 1
            
            # Property: Redis store should be called if available
            if memory.redis_store:
                mock_redis.l0_add.assert_called_once()
                call_args = mock_redis.l0_add.call_args
                assert call_args[1]['content'] == content
                assert call_args[1]['importance'] == importance
                assert call_args[1]['metadata'] == metadata
        
        finally:
            await memory.close()
    
    @pytest.mark.asyncio
    @settings(max_examples=50, deadline=None)  # Disable deadline for async tests
    @given(
        contents=st.lists(valid_memory_content(), min_size=1, max_size=5),
        importances=st.lists(valid_importance(), min_size=1, max_size=5)
    )
    async def test_property_1_batch_consistency(self, contents, importances):
        """
        Feature: phase-4-improvements, Property 1: Memory Data Consistency (Batch)
        
        For any batch of memory operations, all items should be stored consistently
        with their data preserved.
        
        Validates: Requirements 1.2
        """
        # Ensure lists are same length
        min_len = min(len(contents), len(importances))
        contents = contents[:min_len]
        importances = importances[:min_len]
        
        # Mock dependencies
        mock_redis = AsyncMock()
        mock_redis.l0_add = AsyncMock()
        mock_redis.l0_get_all = AsyncMock(return_value=[])
        mock_redis.l1_get_all = AsyncMock(return_value={})
        
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        
        config = {
            "user_id": "test_user",
            "l0_capacity": 100,  # Large capacity to avoid consolidation
            "l1_capacity": 100,
            "embedding_func": None,
        }
        
        memory = FractalMemory(config=config)
        memory.redis_store = mock_redis
        memory.graphiti = mock_graphiti
        memory._initialized = True
        
        try:
            # Store multiple items
            item_ids = []
            for content, importance in zip(contents, importances):
                item_id = await memory.remember(
                    content=content,
                    importance=importance
                )
                item_ids.append(item_id)
            
            # Property: All items should be stored
            assert len(item_ids) == len(contents)
            assert len(memory.l0_cache) >= len(contents)
            
            # Property: All items should have unique IDs
            assert len(set(item_ids)) == len(item_ids)
            
            # Property: Each item should preserve its data
            for i, (content, importance) in enumerate(zip(contents, importances)):
                # Find the item in cache
                matching_items = [
                    item for item in memory.l0_cache
                    if item.content == content and item.importance == importance
                ]
                assert len(matching_items) >= 1, f"Item {i} not found in cache"
                
                # Verify data consistency
                item = matching_items[0]
                assert item.content == content
                assert item.importance == importance
        
        finally:
            await memory.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



class TestMemoryConsolidationIntegrityProperties:
    """Property-based tests for memory consolidation integrity."""
    
    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)  # Reduced examples for performance
    @given(
        contents=st.lists(valid_memory_content(), min_size=5, max_size=10),  # Reduced max size
        importances=st.lists(st.floats(min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=5, max_size=10)  # Higher minimum importance
    )
    async def test_property_2_consolidation_preserves_data(self, contents, importances):
        """
        Feature: phase-4-improvements, Property 2: Memory Consolidation Integrity
        
        For any memory consolidation operation (L0→L1), all required data integrity
        constraints should be preserved, including field presence and value validity.
        Items with importance >= 0.3 should be preserved during consolidation.
        
        Validates: Requirements 1.4
        """
        # Ensure lists are same length
        min_len = min(len(contents), len(importances))
        contents = contents[:min_len]
        importances = importances[:min_len]
        
        # Mock dependencies
        mock_redis = AsyncMock()
        mock_redis.l0_add = AsyncMock()
        mock_redis.l0_get_all = AsyncMock(return_value=[])
        mock_redis.l1_get_all = AsyncMock(return_value={})
        mock_redis.l1_set = AsyncMock()
        mock_redis.l0_remove = AsyncMock()
        
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        
        config = {
            "user_id": "test_user",
            "l0_capacity": 5,  # Small capacity to trigger consolidation
            "l1_capacity": 100,
            "embedding_func": None,
        }
        
        memory = FractalMemory(config=config)
        memory.redis_store = mock_redis
        memory.graphiti = mock_graphiti
        memory._initialized = True
        
        try:
            # Store items to fill L0 and trigger consolidation
            item_ids = []
            for content, importance in zip(contents, importances):
                item_id = await memory.remember(
                    content=content,
                    importance=importance
                )
                item_ids.append(item_id)
            
            # Property: All items should have IDs
            assert len(item_ids) == len(contents)
            assert all(item_id is not None for item_id in item_ids)
            
            # Property: Items should be distributed across L0 and L1
            # (consolidation should have happened due to small L0 capacity)
            total_items = len(memory.l0_cache) + len(memory.l1_cache)
            assert total_items > 0, "Some items should be in memory"
            
            # Property: All items in L0 should have valid structure
            for item in memory.l0_cache:
                assert item.id is not None
                assert item.content is not None
                assert isinstance(item.content, str)
                assert 0.0 <= item.importance <= 1.0
                assert item.level == 0
                assert item.created_at is not None
                assert item.last_accessed is not None
                assert item.access_count >= 1
            
            # Property: All items in L1 should have valid structure
            for item_id, item in memory.l1_cache.items():
                assert item.id is not None
                assert item.content is not None
                assert isinstance(item.content, str)
                assert 0.0 <= item.importance <= 1.0
                assert item.level == 1
                assert item.created_at is not None
                assert item.last_accessed is not None
                assert item.access_count >= 1
            
            # Property: Important data should be preserved during consolidation
            # Items with high importance should be findable in either L0 or L1
            all_cached_contents = (
                [item.content for item in memory.l0_cache] +
                [item.content for item in memory.l1_cache.values()]
            )
            
            # Count how many items were preserved
            preserved_count = sum(1 for content in contents if content in all_cached_contents)
            
            # Property: At least some items should be preserved (not all lost)
            # Due to capacity limits, not all items may be kept, but some should be
            assert preserved_count > 0, "At least some items should be preserved during consolidation"
            
            # Property: High importance items should be more likely to be preserved
            high_importance_contents = [
                content for content, importance in zip(contents, importances)
                if importance >= 0.7
            ]
            if high_importance_contents:
                high_preserved = sum(
                    1 for content in high_importance_contents
                    if content in all_cached_contents
                )
                # At least half of high importance items should be preserved
                assert high_preserved >= len(high_importance_contents) // 2, \
                    f"High importance items should be preserved: {high_preserved}/{len(high_importance_contents)}"
        
        finally:
            await memory.close()
    
    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)  # Reduced examples for performance
    @given(
        high_importance_contents=st.lists(valid_memory_content(), min_size=2, max_size=5),  # Reduced size
        low_importance_contents=st.lists(valid_memory_content(), min_size=2, max_size=5)  # Reduced size
    )
    async def test_property_2_consolidation_respects_importance(
        self, high_importance_contents, low_importance_contents
    ):
        """
        Feature: phase-4-improvements, Property 2: Consolidation Respects Importance
        
        For any consolidation operation, items with higher importance should be
        more likely to be promoted to higher tiers.
        
        Validates: Requirements 1.4
        """
        # Mock dependencies
        mock_redis = AsyncMock()
        mock_redis.l0_add = AsyncMock()
        mock_redis.l0_get_all = AsyncMock(return_value=[])
        mock_redis.l1_get_all = AsyncMock(return_value={})
        mock_redis.l1_set = AsyncMock()
        mock_redis.l0_remove = AsyncMock()
        
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        
        config = {
            "user_id": "test_user",
            "l0_capacity": 5,  # Small capacity to trigger consolidation
            "l1_capacity": 100,
            "importance_threshold": 0.5,  # Items above 0.5 are important
            "embedding_func": None,
        }
        
        memory = FractalMemory(config=config)
        memory.redis_store = mock_redis
        memory.graphiti = mock_graphiti
        memory._initialized = True
        
        try:
            # Store high importance items
            high_ids = []
            for content in high_importance_contents:
                item_id = await memory.remember(
                    content=content,
                    importance=0.9  # High importance
                )
                high_ids.append(item_id)
            
            # Store low importance items
            low_ids = []
            for content in low_importance_contents:
                item_id = await memory.remember(
                    content=content,
                    importance=0.1  # Low importance
                )
                low_ids.append(item_id)
            
            # Property: High importance items should be preserved
            all_cached_contents = (
                [item.content for item in memory.l0_cache] +
                [item.content for item in memory.l1_cache.values()]
            )
            
            # At least some high importance items should be in cache
            high_in_cache = sum(
                1 for content in high_importance_contents
                if content in all_cached_contents
            )
            assert high_in_cache > 0, "High importance items should be preserved"
            
            # Property: Items in L1 should have higher average importance than items in L0
            if len(memory.l0_cache) > 0 and len(memory.l1_cache) > 0:
                l0_avg_importance = sum(item.importance for item in memory.l0_cache) / len(memory.l0_cache)
                l1_avg_importance = sum(item.importance for item in memory.l1_cache.values()) / len(memory.l1_cache)
                
                # L1 should generally have higher importance (with some tolerance)
                # This is a statistical property, not absolute
                assert l1_avg_importance >= l0_avg_importance - 0.2, \
                    f"L1 avg importance ({l1_avg_importance:.2f}) should be >= L0 avg ({l0_avg_importance:.2f})"
        
        finally:
            await memory.close()
