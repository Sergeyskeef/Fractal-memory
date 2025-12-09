"""
Schema validator for Neo4j database.

Checks:
- Cypher queries reference valid node labels and properties
- Relationships are correctly defined
- Required indexes exist
- Schema matches code expectations
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from ..core.base_checker import StaticChecker
from ..core.models import Issue, Category, Severity, Neo4jSchema
from ..config import AuditConfig


class SchemaValidator(StaticChecker):
    """Проверка соответствия кода схеме Neo4j."""
    
    # Known Graphiti-managed patterns (from Graphiti library)
    GRAPHITI_INDEXES = {
        'entity_uuid', 'episode_uuid', 'relation_uuid',
        'entity_group_id', 'episode_group_id', 'relation_group_id',
        'name_entity_index', 'name_edge_index',
        'created_at_entity_index', 'created_at_episodic_index',
        'valid_at_episodic_index', 'invalid_at_edge_index',
        'episode_content', 'node_name_and_summary', 'edge_name_and_fact',
        'community_uuid', 'community_group_id', 'community_name',
        'mention_uuid', 'mention_group_id', 'has_member_uuid',
    }
    
    GRAPHITI_NODE_LABELS = {'Entity', 'Episodic', 'Community'}
    GRAPHITI_RELATIONSHIPS = {'RELATES_TO', 'MENTIONS', 'HAS_MEMBER'}
    
    def __init__(self, config: AuditConfig):
        super().__init__(name="SchemaValidator", timeout_seconds=config.default_timeout_seconds)
        self.config = config
        self._schema_cache: Optional[Neo4jSchema] = None
    
    def is_graphiti_managed(self, element_name: str) -> bool:
        """
        Check if an element (index, label, relationship) is managed by Graphiti.
        
        Args:
            element_name: Name of the element to check
        
        Returns:
            True if element is managed by Graphiti, False otherwise
        """
        # Check if it's a known Graphiti index
        if element_name in self.GRAPHITI_INDEXES:
            return True
        
        # Check if it's a known Graphiti node label
        if element_name in self.GRAPHITI_NODE_LABELS:
            return True
        
        # Check if it's a known Graphiti relationship
        if element_name in self.GRAPHITI_RELATIONSHIPS:
            return True
        
        # Check for common Graphiti patterns in index names
        graphiti_patterns = [
            'entity_', 'episode_', 'episodic_', 'relation_',
            'community_', 'mention_', 'has_member_',
            '_uuid', '_group_id', '_index'
        ]
        
        element_lower = element_name.lower()
        for pattern in graphiti_patterns:
            if pattern in element_lower:
                return True
        
        return False
    
    async def _check(self) -> List[Issue]:
        """Выполнить все проверки схемы."""
        issues = []
        
        # Get actual schema from Neo4j
        try:
            schema = await self.get_actual_schema()
            self.logger.info(f"Retrieved schema: {len(schema.node_labels)} node labels, "
                           f"{len(schema.relationships)} relationships")
        except Exception as e:
            self.logger.error(f"Failed to get Neo4j schema: {e}")
            issues.append(self.create_issue(
                category=Category.SCHEMA,
                severity=Severity.CRITICAL,
                title="Cannot connect to Neo4j",
                description=f"Failed to retrieve schema: {str(e)}",
                location="Neo4j connection",
                impact="Cannot validate schema consistency",
                recommendation="Check Neo4j connection settings and ensure database is running",
            ))
            return issues
        
        # Validate Cypher queries in Python files
        python_files = self.config.get_python_files()
        self.logger.info(f"Validating Cypher queries in {len(python_files)} Python files...")
        for file_path in python_files:
            issues.extend(await self.validate_cypher_queries(file_path, schema))
        
        # Check node labels usage
        self.logger.info("Checking node labels...")
        issues.extend(await self.check_node_labels(schema))
        
        # Check relationships
        self.logger.info("Checking relationships...")
        issues.extend(await self.check_relationships(schema))
        
        # Check indexes
        self.logger.info("Checking indexes...")
        issues.extend(await self.check_indexes(schema))
        
        return issues
    
    async def get_actual_schema(self) -> Neo4jSchema:
        """
        Получить реальную схему из Neo4j.
        
        Returns:
            Neo4jSchema с информацией о метках, полях, связях, индексах
        """
        if self._schema_cache is not None:
            return self._schema_cache
        
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("neo4j driver not installed. Install with: pip install neo4j")
        
        driver = GraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password)
        )
        
        try:
            with driver.session() as session:
                # Get node labels and their properties
                node_labels = {}
                
                # Get all labels
                result = session.run("CALL db.labels()")
                labels = [record["label"] for record in result]
                
                # For each label, get its properties
                for label in labels:
                    # Get sample node to extract properties
                    result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 1")
                    record = result.single()
                    if record:
                        node = record["n"]
                        properties = list(node.keys())
                        node_labels[label] = properties
                    else:
                        node_labels[label] = []
                
                # Get relationships
                relationships = []
                result = session.run("""
                    CALL db.relationshipTypes() YIELD relationshipType
                    RETURN relationshipType
                """)
                rel_types = [record["relationshipType"] for record in result]
                
                # For each relationship type, find examples of source and target labels
                for rel_type in rel_types:
                    result = session.run(f"""
                        MATCH (a)-[r:{rel_type}]->(b)
                        RETURN DISTINCT labels(a) as from_labels, labels(b) as to_labels
                        LIMIT 10
                    """)
                    
                    for record in result:
                        from_labels = record["from_labels"]
                        to_labels = record["to_labels"]
                        
                        # Add all combinations
                        for from_label in from_labels:
                            for to_label in to_labels:
                                rel_tuple = (from_label, rel_type, to_label)
                                if rel_tuple not in relationships:
                                    relationships.append(rel_tuple)
                
                # Get indexes
                indexes = []
                result = session.run("SHOW INDEXES")
                for record in result:
                    index_name = record.get("name", "")
                    indexes.append(index_name)
                
                # Get constraints
                constraints = []
                result = session.run("SHOW CONSTRAINTS")
                for record in result:
                    constraint_name = record.get("name", "")
                    constraints.append(constraint_name)
                
                schema = Neo4jSchema(
                    node_labels=node_labels,
                    relationships=relationships,
                    indexes=indexes,
                    constraints=constraints,
                )
                
                self._schema_cache = schema
                return schema
        
        finally:
            driver.close()
    
    async def validate_cypher_queries(self, file_path: Path, schema: Neo4jSchema) -> List[Issue]:
        """
        Проверить Cypher запросы в файле.
        
        Args:
            file_path: Путь к Python файлу
            schema: Схема Neo4j
        
        Returns:
            Список найденных проблем
        """
        issues = []
        
        # Skip test files for SchemaValidator itself (they contain test data)
        if 'test_schema_validator.py' in str(file_path):
            return issues
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find Cypher queries (in strings)
            # Look for common patterns: MATCH, CREATE, MERGE, etc.
            cypher_patterns = [
                r'["\']([^"\']*(?:MATCH|CREATE|MERGE|RETURN|WHERE|SET|DELETE)[^"\']*)["\']',
                r'"""([^"]*(?:MATCH|CREATE|MERGE|RETURN|WHERE|SET|DELETE)[^"]*)"""',
                r"'''([^']*(?:MATCH|CREATE|MERGE|RETURN|WHERE|SET|DELETE)[^']*)'''",
            ]
            
            for pattern in cypher_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                    query = match.group(1)
                    line_no = content[:match.start()].count('\n') + 1
                    
                    # Validate query
                    query_issues = self._validate_query(query, schema, file_path, line_no)
                    issues.extend(query_issues)
        
        except Exception as e:
            self.logger.warning(f"Error validating Cypher in {file_path}: {e}")
        
        return issues
    
    def _validate_query(
        self, 
        query: str, 
        schema: Neo4jSchema, 
        file_path: Path, 
        line_no: int
    ) -> List[Issue]:
        """
        Проверить один Cypher запрос.
        
        Args:
            query: Cypher запрос
            schema: Схема Neo4j
            file_path: Файл с запросом
            line_no: Номер строки
        
        Returns:
            Список проблем
        """
        issues = []
        
        # Extract node labels from query
        # Pattern: (variable:Label) or (:Label)
        # Must have at least one letter before the colon to avoid matching array slices like [:20]
        label_pattern = r'\([a-zA-Z_]\w*:(\w+)[^)]*\)|:\s*(\w+)\s*\)'
        matches = re.findall(label_pattern, query)
        labels_in_query = [m[0] or m[1] for m in matches if m[0] or m[1]]
        
        for label in labels_in_query:
            # Skip numeric labels (likely false positives from array slices)
            if label.isdigit():
                continue
            
            if not schema.has_node_label(label):
                issues.append(self.create_issue(
                    category=Category.SCHEMA,
                    severity=Severity.HIGH,
                    title=f"Unknown node label: {label}",
                    description=f"Query references node label '{label}' which doesn't exist in Neo4j schema",
                    location=f"{file_path}:{line_no}",
                    impact="Query will not match any nodes",
                    recommendation=f"Use one of the existing labels: {', '.join(schema.node_labels.keys())}",
                    code_snippet=query[:200],
                ))
        
        # Extract property accesses from query
        # Pattern: variable.property or n.property
        property_pattern = r'(\w+)\.(\w+)'
        properties_in_query = re.findall(property_pattern, query)
        
        # Try to match properties with labels
        # This is heuristic - we look for label definitions before property access
        for var_name, prop_name in properties_in_query:
            # Find label for this variable
            var_label_pattern = rf'\({var_name}:(\w+)\)'
            var_labels = re.findall(var_label_pattern, query)
            
            for label in var_labels:
                if schema.has_node_label(label):
                    if not schema.has_node_field(label, prop_name):
                        issues.append(self.create_issue(
                            category=Category.SCHEMA,
                            severity=Severity.HIGH,
                            title=f"Unknown property: {label}.{prop_name}",
                            description=f"Query accesses property '{prop_name}' on label '{label}' which doesn't exist",
                            location=f"{file_path}:{line_no}",
                            impact="Query may fail or return unexpected results",
                            recommendation=f"Use one of the existing properties for {label}: {', '.join(schema.node_labels.get(label, []))}",
                            code_snippet=query[:200],
                        ))
        
        # Extract relationship types from query
        # Pattern: -[:REL_TYPE]-> or -[r:REL_TYPE]->
        rel_pattern = r'-\[[^]]*:(\w+)[^]]*\]->'
        rels_in_query = re.findall(rel_pattern, query)
        
        for rel_type in rels_in_query:
            # Check if relationship type exists
            rel_exists = any(rel[1] == rel_type for rel in schema.relationships)
            if not rel_exists:
                issues.append(self.create_issue(
                    category=Category.SCHEMA,
                    severity=Severity.MEDIUM,
                    title=f"Unknown relationship type: {rel_type}",
                    description=f"Query uses relationship type '{rel_type}' which doesn't exist in Neo4j",
                    location=f"{file_path}:{line_no}",
                    impact="Query will not match any relationships",
                    recommendation=f"Use one of the existing relationship types",
                    code_snippet=query[:200],
                ))
        
        return issues
    
    async def check_node_labels(self, schema: Neo4jSchema) -> List[Issue]:
        """
        Проверить использование меток узлов.
        
        Args:
            schema: Схема Neo4j
        
        Returns:
            Список проблем
        """
        issues = []
        
        # Expected labels based on REAL architecture
        # L0/L1 находятся в Redis, не в Neo4j!
        expected_labels = {
            'Episodic',      # L2 - долгосрочная эпизодическая память (Graphiti)
            'Entity',        # L2 - сущности (Graphiti)
            'Strategy',      # L3 - стратегии обучения (ReasoningBank)
            'Experience',    # L3 - опыт применения стратегий (ReasoningBank)
        }
        
        # Optional labels (могут быть, но не обязательны)
        optional_labels = {
            'Community',     # Graphiti communities (опционально)
            'Migration',     # Служебная метка для миграций
        }
        
        # Check for missing expected labels
        for label in expected_labels:
            if not schema.has_node_label(label):
                # Check if it's a Graphiti-managed label
                is_graphiti = self.is_graphiti_managed(label)
                
                # Reduce severity for Graphiti labels (they may not exist if no data yet)
                severity = Severity.MEDIUM if is_graphiti else Severity.HIGH
                
                issues.append(self.create_issue(
                    category=Category.SCHEMA,
                    severity=severity,
                    title=f"Missing expected node label: {label}",
                    description=f"Expected node label '{label}' not found in Neo4j schema" + 
                               (" (Graphiti-managed, may not exist until data is added)" if is_graphiti else ""),
                    location="Neo4j schema",
                    impact="Memory architecture may not be working as designed" if not is_graphiti else 
                           "Graphiti label missing, but will be created when data is added",
                    recommendation=f"Ensure migrations create the {label} label, or check if data exists" if not is_graphiti else
                                 f"Add data to trigger Graphiti to create the {label} label",
                ))
        
        # Check for unexpected labels (might indicate issues)
        actual_labels = set(schema.node_labels.keys())
        all_known_labels = expected_labels | optional_labels
        unexpected_labels = actual_labels - all_known_labels
        
        # Filter out Graphiti-managed labels from unexpected
        non_graphiti_unexpected = {
            label for label in unexpected_labels
            if not self.is_graphiti_managed(label)
        }
        
        if non_graphiti_unexpected:
            issues.append(self.create_issue(
                category=Category.SCHEMA,
                severity=Severity.LOW,
                title=f"Unexpected node labels found",
                description=f"Found labels not in expected set: {', '.join(non_graphiti_unexpected)}",
                location="Neo4j schema",
                impact="May indicate unused or legacy data",
                recommendation="Review if these labels are intentional or should be cleaned up",
            ))
        
        # Log Graphiti-managed labels (informational)
        graphiti_labels = {label for label in actual_labels if self.is_graphiti_managed(label)}
        if graphiti_labels:
            self.logger.info(f"Found {len(graphiti_labels)} Graphiti-managed labels: {', '.join(graphiti_labels)}")
        
        return issues
    
    async def check_relationships(self, schema: Neo4jSchema) -> List[Issue]:
        """
        Проверить связи между узлами.
        
        Args:
            schema: Схема Neo4j
        
        Returns:
            Список проблем
        """
        issues = []
        
        # Expected relationships based on REAL architecture
        expected_relationships = [
            # Graphiti relationships (L2)
            ('Episodic', 'MENTIONS', 'Entity'),           # Эпизод упоминает сущность
            ('Entity', 'RELATES_TO', 'Entity'),           # Сущность связана с сущностью
            
            # ReasoningBank relationships (L3)
            ('Experience', 'USED_STRATEGY', 'Strategy'),  # Опыт использовал стратегию
        ]
        
        # Optional relationships (могут быть, но не обязательны)
        optional_relationships = [
            ('Entity', 'IN_COMMUNITY', 'Community'),      # Graphiti communities
            ('Community', 'HAS_MEMBER', 'Entity'),        # Graphiti communities
        ]
        
        # Check for missing expected relationships
        for from_label, rel_type, to_label in expected_relationships:
            if not schema.has_relationship(from_label, rel_type, to_label):
                # Check if it's a Graphiti-managed relationship
                is_graphiti = self.is_graphiti_managed(rel_type)
                
                # Reduce severity for Graphiti relationships (they may not exist if no data yet)
                severity = Severity.LOW if is_graphiti else Severity.MEDIUM
                
                issues.append(self.create_issue(
                    category=Category.SCHEMA,
                    severity=severity,
                    title=f"Missing expected relationship: ({from_label})-[:{rel_type}]->({to_label})",
                    description=f"Expected relationship not found in Neo4j schema" +
                               (" (Graphiti-managed, may not exist until data is added)" if is_graphiti else ""),
                    location="Neo4j schema",
                    impact="Memory consolidation or retrieval may not work correctly" if not is_graphiti else
                           "Graphiti relationship missing, but will be created when data is added",
                    recommendation=f"Check if data with this relationship exists, or if code creates it" if not is_graphiti else
                                 f"Add data to trigger Graphiti to create the relationship",
                ))
        
        # Log Graphiti-managed relationships (informational)
        graphiti_rels = [
            rel for rel in schema.relationships
            if self.is_graphiti_managed(rel[1])  # rel[1] is the relationship type
        ]
        if graphiti_rels:
            self.logger.info(f"Found {len(graphiti_rels)} Graphiti-managed relationships")
        
        return issues
    
    async def check_indexes(self, schema: Neo4jSchema) -> List[Issue]:
        """
        Проверить наличие необходимых индексов.
        
        Args:
            schema: Схема Neo4j
        
        Returns:
            Список проблем
        """
        issues = []
        
        # Expected indexes for performance (non-Graphiti)
        # Note: Actual index names may vary, so we check for patterns
        expected_index_patterns = [
            'uuid',           # For UUID lookups
            'embedding',      # For vector search
            'content',        # For fulltext search
            'created_at',     # For time-based queries
        ]
        
        # Count Graphiti-managed indexes (informational)
        graphiti_indexes = [idx for idx in schema.indexes if self.is_graphiti_managed(idx)]
        self.logger.info(f"Found {len(graphiti_indexes)} Graphiti-managed indexes (expected)")
        
        # Check if we have indexes that match expected patterns
        # Only report missing indexes if they're not Graphiti-managed
        for pattern in expected_index_patterns:
            has_matching_index = any(pattern in idx.lower() for idx in schema.indexes)
            
            if not has_matching_index:
                # Check if Graphiti provides this functionality
                graphiti_provides = any(
                    pattern in idx.lower() for idx in graphiti_indexes
                )
                
                if not graphiti_provides:
                    issues.append(self.create_issue(
                        category=Category.SCHEMA,
                        severity=Severity.LOW,  # Reduced severity since Graphiti may handle this
                        title=f"Missing index for: {pattern}",
                        description=f"No index found matching pattern '{pattern}' (Graphiti may provide this)",
                        location="Neo4j schema",
                        impact="Queries may be slow without proper indexes (unless Graphiti handles it)",
                        recommendation=f"Create index for {pattern} field to improve query performance, or verify Graphiti provides this",
                    ))
        
        return issues
