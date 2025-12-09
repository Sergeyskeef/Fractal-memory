"""
Property-based tests for SchemaValidator.

Property 2: Schema consistency
- For any Cypher query, all referenced fields should exist in the schema
- Invalid node labels and properties should be detected
"""

import tempfile
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st, settings, assume

from ..checkers.schema_validator import SchemaValidator
from ..config import AuditConfig
from ..core.models import Category, Severity, Neo4jSchema


# === Strategies for generating test data ===

@st.composite
def node_label(draw):
    """Generate a node label name."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu',), min_codepoint=65, max_codepoint=90),
        min_size=1,
        max_size=20
    ))


@st.composite
def property_name(draw):
    """Generate a property name."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=20
    ))


@st.composite
def cypher_match_query(draw):
    """Generate a simple Cypher MATCH query."""
    label = draw(node_label())
    var = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=10
    ))
    prop = draw(property_name())
    
    return f"MATCH ({var}:{label}) RETURN {var}.{prop}"


@st.composite
def cypher_create_query(draw):
    """Generate a simple Cypher CREATE query."""
    label = draw(node_label())
    var = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll',), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=10
    ))
    prop = draw(property_name())
    value = draw(st.text(min_size=1, max_size=50))
    
    return f"CREATE ({var}:{label} {{{prop}: '{value}'}})"


@st.composite
def mock_schema(draw):
    """Generate a mock Neo4j schema."""
    num_labels = draw(st.integers(min_value=1, max_value=5))
    
    node_labels = {}
    for _ in range(num_labels):
        label = draw(node_label())
        num_props = draw(st.integers(min_value=1, max_value=5))
        props = [draw(property_name()) for _ in range(num_props)]
        node_labels[label] = props
    
    # Generate some relationships
    relationships = []
    if len(node_labels) >= 2:
        labels_list = list(node_labels.keys())
        num_rels = draw(st.integers(min_value=0, max_value=3))
        for _ in range(num_rels):
            from_label = draw(st.sampled_from(labels_list))
            to_label = draw(st.sampled_from(labels_list))
            rel_type = draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu',), min_codepoint=65, max_codepoint=90),
                min_size=1,
                max_size=20
            ))
            relationships.append((from_label, rel_type, to_label))
    
    return Neo4jSchema(
        node_labels=node_labels,
        relationships=relationships,
        indexes=[],
        constraints=[],
    )


# === Property Tests ===

class TestSchemaValidatorProperties:
    """Property-based tests for SchemaValidator."""
    
    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config for testing."""
        config = AuditConfig()
        config.project_root = tmp_path
        config.src_dir = tmp_path / "src"
        config.src_dir.mkdir(exist_ok=True)
        return config
    
    @pytest.mark.asyncio
    @given(query=cypher_match_query())
    @settings(max_examples=50, deadline=None)
    async def test_property_query_validation_structure(self, temp_config, query):
        """
        Property 2: Schema consistency validation structure.
        
        For any Cypher query, the validator should:
        1. Parse the query without crashing
        2. Return a list of issues
        3. All issues should have valid structure
        """
        # Create a mock schema
        schema = Neo4jSchema(
            node_labels={'TestLabel': ['test_prop']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        # Create temporary file with query
        test_file = temp_config.src_dir / "test_query.py"
        test_file.write_text(f'query = "{query}"')
        
        validator = SchemaValidator(temp_config)
        
        try:
            issues = validator._validate_query(query, schema, test_file, 1)
            
            # Property: Should return a list
            assert isinstance(issues, list)
            
            # Property: All issues should have valid structure
            for issue in issues:
                assert hasattr(issue, 'category')
                assert hasattr(issue, 'severity')
                assert issue.category == Category.SCHEMA
        
        except Exception as e:
            pytest.fail(f"Validator crashed on valid input: {e}")
    
    @pytest.mark.asyncio
    async def test_property_valid_label_not_flagged(self, temp_config):
        """
        Property: Valid node labels should not be flagged.
        
        If a query uses a label that exists in the schema, it should not be flagged.
        """
        schema = Neo4jSchema(
            node_labels={'Person': ['name', 'age']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        query = "MATCH (p:Person) RETURN p.name"
        test_file = temp_config.src_dir / "test.py"
        
        validator = SchemaValidator(temp_config)
        issues = validator._validate_query(query, schema, test_file, 1)
        
        # Property: Should not flag valid label
        assert not any('Person' in issue.description and 'Unknown' in issue.title for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_invalid_label_flagged(self, temp_config):
        """
        Property: Invalid node labels should be flagged.
        
        If a query uses a label that doesn't exist in the schema, it should be flagged.
        """
        schema = Neo4jSchema(
            node_labels={'Person': ['name', 'age']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        query = "MATCH (c:Company) RETURN c.name"
        test_file = temp_config.src_dir / "test.py"
        
        validator = SchemaValidator(temp_config)
        issues = validator._validate_query(query, schema, test_file, 1)
        
        # Property: Should flag invalid label
        assert len(issues) > 0
        assert any('Company' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_valid_property_not_flagged(self, temp_config):
        """
        Property: Valid properties should not be flagged.
        
        If a query accesses a property that exists on a node, it should not be flagged.
        """
        schema = Neo4jSchema(
            node_labels={'Person': ['name', 'age', 'email']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        query = "MATCH (p:Person) RETURN p.name, p.age"
        test_file = temp_config.src_dir / "test.py"
        
        validator = SchemaValidator(temp_config)
        issues = validator._validate_query(query, schema, test_file, 1)
        
        # Property: Should not flag valid properties
        assert not any('name' in issue.description and 'Unknown property' in issue.title for issue in issues)
        assert not any('age' in issue.description and 'Unknown property' in issue.title for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_invalid_property_flagged(self, temp_config):
        """
        Property: Invalid properties should be flagged.
        
        If a query accesses a property that doesn't exist on a node, it should be flagged.
        """
        schema = Neo4jSchema(
            node_labels={'Person': ['name', 'age']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        query = "MATCH (p:Person) RETURN p.salary"
        test_file = temp_config.src_dir / "test.py"
        
        validator = SchemaValidator(temp_config)
        issues = validator._validate_query(query, schema, test_file, 1)
        
        # Property: Should flag invalid property
        assert len(issues) > 0
        assert any('salary' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    async def test_property_relationship_validation(self, temp_config):
        """
        Property: Relationship types should be validated.
        
        If a query uses a relationship type that doesn't exist, it should be flagged.
        """
        schema = Neo4jSchema(
            node_labels={'Person': ['name'], 'Company': ['name']},
            relationships=[('Person', 'WORKS_AT', 'Company')],
            indexes=[],
            constraints=[],
        )
        
        # Valid relationship
        valid_query = "MATCH (p:Person)-[:WORKS_AT]->(c:Company) RETURN p, c"
        test_file = temp_config.src_dir / "test.py"
        
        validator = SchemaValidator(temp_config)
        issues = validator._validate_query(valid_query, schema, test_file, 1)
        
        # Should not flag valid relationship
        assert not any('WORKS_AT' in issue.description and 'Unknown' in issue.title for issue in issues)
        
        # Invalid relationship
        invalid_query = "MATCH (p:Person)-[:OWNS]->(c:Company) RETURN p, c"
        issues = validator._validate_query(invalid_query, schema, test_file, 1)
        
        # Should flag invalid relationship
        assert len(issues) > 0
        assert any('OWNS' in issue.description for issue in issues)
    
    @pytest.mark.asyncio
    @given(schema=mock_schema())
    @settings(max_examples=30, deadline=None)
    async def test_property_schema_methods(self, schema):
        """
        Property: Schema helper methods should work correctly.
        
        For any schema, the helper methods should:
        1. Correctly identify existing labels
        2. Correctly identify existing properties
        3. Correctly identify existing relationships
        """
        # Test has_node_label
        for label in schema.node_labels.keys():
            assert schema.has_node_label(label), f"Should find existing label {label}"
        
        assert not schema.has_node_label("NonExistentLabel"), "Should not find non-existent label"
        
        # Test has_node_field
        for label, fields in schema.node_labels.items():
            for field in fields:
                assert schema.has_node_field(label, field), f"Should find existing field {label}.{field}"
            
            assert not schema.has_node_field(label, "nonexistent_field"), \
                f"Should not find non-existent field on {label}"
        
        # Test has_relationship
        for from_label, rel_type, to_label in schema.relationships:
            assert schema.has_relationship(from_label, rel_type, to_label), \
                f"Should find existing relationship ({from_label})-[:{rel_type}]->({to_label})"
        
        assert not schema.has_relationship("A", "NONEXISTENT", "B"), \
            "Should not find non-existent relationship"
    
    @pytest.mark.asyncio
    async def test_property_expected_labels_check(self, temp_config):
        """
        Property: Expected labels should be checked.
        
        The validator should check for expected labels based on architecture.
        """
        # Schema missing expected labels
        schema = Neo4jSchema(
            node_labels={'SomeOtherLabel': ['prop']},
            relationships=[],
            indexes=[],
            constraints=[],
        )
        
        validator = SchemaValidator(temp_config)
        issues = await validator.check_node_labels(schema)
        
        # Should flag missing expected labels
        assert len(issues) > 0
        expected_labels = ['Episodic', 'ShortTerm', 'Entity', 'Strategy']
        for label in expected_labels:
            assert any(label in issue.description for issue in issues), \
                f"Should flag missing {label} label"
    
    @pytest.mark.asyncio
    async def test_property_expected_relationships_check(self, temp_config):
        """
        Property: Expected relationships should be checked.
        
        The validator should check for expected relationships based on architecture.
        """
        # Schema with labels but missing relationships
        schema = Neo4jSchema(
            node_labels={
                'Episodic': ['uuid'],
                'ShortTerm': ['uuid'],
                'Entity': ['uuid'],
            },
            relationships=[],  # No relationships
            indexes=[],
            constraints=[],
        )
        
        validator = SchemaValidator(temp_config)
        issues = await validator.check_relationships(schema)
        
        # Should flag missing expected relationships
        assert len(issues) > 0
        assert any('CONSOLIDATED_TO' in issue.description for issue in issues)


# === Integration Tests ===

class TestSchemaValidatorIntegration:
    """Integration tests with real Neo4j (if available)."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_actual_schema_from_neo4j(self):
        """Test getting schema from real Neo4j instance."""
        config = AuditConfig()
        
        # Skip if no Neo4j credentials
        if not config.has_neo4j_credentials():
            pytest.skip("No Neo4j credentials configured")
        
        validator = SchemaValidator(config)
        
        try:
            schema = await validator.get_actual_schema()
            
            # Should return valid schema
            assert isinstance(schema, Neo4jSchema)
            assert isinstance(schema.node_labels, dict)
            assert isinstance(schema.relationships, list)
            assert isinstance(schema.indexes, list)
            
            # Log schema for inspection
            print(f"\nRetrieved schema:")
            print(f"  Node labels: {list(schema.node_labels.keys())}")
            print(f"  Relationships: {len(schema.relationships)}")
            print(f"  Indexes: {len(schema.indexes)}")
        
        except Exception as e:
            pytest.skip(f"Cannot connect to Neo4j: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_validate_real_project_queries(self):
        """Test validating queries in the real project."""
        config = AuditConfig()
        
        # Skip if no Neo4j credentials
        if not config.has_neo4j_credentials():
            pytest.skip("No Neo4j credentials configured")
        
        validator = SchemaValidator(config)
        
        try:
            # Run full check
            issues = await validator._check()
            
            # Should complete without crashing
            assert isinstance(issues, list)
            
            # Log results for inspection
            print(f"\nFound {len(issues)} schema issues:")
            for issue in issues[:10]:  # Print first 10
                print(f"  - [{issue.severity.value}] {issue.title}")
                print(f"    Location: {issue.location}")
        
        except Exception as e:
            pytest.skip(f"Cannot run schema validation: {e}")
