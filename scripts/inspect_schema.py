#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
Schema Inspector - Исследование схемы Neo4j
═══════════════════════════════════════════════════════

Этот скрипт подключается к Neo4j и показывает:
1. Все метки узлов (labels)
2. Все типы связей (relationships)
3. Примеры узлов с их свойствами
4. Индексы и ограничения
"""

import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed")

from neo4j import GraphDatabase


def inspect_schema():
    """Исследовать схему Neo4j."""
    
    # Подключение
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', '')
    
    print("=" * 70)
    print("🔍 NEO4J SCHEMA INSPECTOR")
    print("=" * 70)
    print(f"📡 Connecting to: {uri}")
    print()
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # 1. Получить все метки узлов
            print("📋 NODE LABELS:")
            print("-" * 70)
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            
            if labels:
                for i, label in enumerate(labels, 1):
                    print(f"  {i}. {label}")
            else:
                print("  ⚠️  No labels found in database")
            
            print()
            
            # 2. Получить все типы связей
            print("🔗 RELATIONSHIP TYPES:")
            print("-" * 70)
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            
            if rel_types:
                for i, rel_type in enumerate(rel_types, 1):
                    print(f"  {i}. {rel_type}")
            else:
                print("  ⚠️  No relationship types found")
            
            print()
            
            # 3. Показать примеры узлов для каждой метки
            print("📦 NODE EXAMPLES (with properties):")
            print("-" * 70)
            
            for label in labels[:10]:  # Первые 10 меток
                result = session.run(f"""
                    MATCH (n:{label})
                    RETURN n
                    LIMIT 1
                """)
                
                record = result.single()
                if record:
                    node = record["n"]
                    props = dict(node.items())
                    
                    print(f"\n  Label: {label}")
                    print(f"  Properties:")
                    for key, value in props.items():
                        # Обрезать длинные значения
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        print(f"    - {key}: {value_str}")
            
            print()
            
            # 4. Показать связи между узлами
            print("🔗 RELATIONSHIP EXAMPLES:")
            print("-" * 70)
            
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN labels(a) as from_labels, type(r) as rel_type, labels(b) as to_labels
                LIMIT 10
            """)
            
            relationships = []
            for record in result:
                from_labels = record["from_labels"]
                rel_type = record["rel_type"]
                to_labels = record["to_labels"]
                
                for from_label in from_labels:
                    for to_label in to_labels:
                        rel = (from_label, rel_type, to_label)
                        if rel not in relationships:
                            relationships.append(rel)
            
            if relationships:
                for i, (from_label, rel_type, to_label) in enumerate(relationships, 1):
                    print(f"  {i}. ({from_label})-[:{rel_type}]->({to_label})")
            else:
                print("  ⚠️  No relationships found")
            
            print()
            
            # 5. Показать индексы
            print("📇 INDEXES:")
            print("-" * 70)
            
            try:
                result = session.run("SHOW INDEXES")
                indexes = []
                for record in result:
                    index_name = record.get("name", "")
                    index_type = record.get("type", "")
                    labels_or_types = record.get("labelsOrTypes", [])
                    properties = record.get("properties", [])
                    
                    indexes.append({
                        "name": index_name,
                        "type": index_type,
                        "labels": labels_or_types,
                        "properties": properties
                    })
                
                if indexes:
                    for i, idx in enumerate(indexes, 1):
                        print(f"  {i}. {idx['name']}")
                        print(f"     Type: {idx['type']}")
                        print(f"     Labels: {idx['labels']}")
                        print(f"     Properties: {idx['properties']}")
                        print()
                else:
                    print("  ⚠️  No indexes found")
            except Exception as e:
                print(f"  ⚠️  Could not retrieve indexes: {e}")
            
            print()
            
            # 6. Показать ограничения
            print("🔒 CONSTRAINTS:")
            print("-" * 70)
            
            try:
                result = session.run("SHOW CONSTRAINTS")
                constraints = []
                for record in result:
                    constraint_name = record.get("name", "")
                    constraint_type = record.get("type", "")
                    
                    constraints.append({
                        "name": constraint_name,
                        "type": constraint_type
                    })
                
                if constraints:
                    for i, const in enumerate(constraints, 1):
                        print(f"  {i}. {const['name']} ({const['type']})")
                else:
                    print("  ⚠️  No constraints found")
            except Exception as e:
                print(f"  ⚠️  Could not retrieve constraints: {e}")
            
            print()
            
            # 7. Статистика
            print("📊 DATABASE STATISTICS:")
            print("-" * 70)
            
            # Количество узлов
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            print(f"  Total nodes: {node_count}")
            
            # Количество связей
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"  Total relationships: {rel_count}")
            
            # Количество узлов по меткам
            print(f"\n  Nodes by label:")
            for label in labels:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"    - {label}: {count}")
            
            print()
            print("=" * 70)
            print("✅ Schema inspection complete!")
            print("=" * 70)
    
    finally:
        driver.close()


if __name__ == "__main__":
    try:
        inspect_schema()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
