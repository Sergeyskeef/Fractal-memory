#!/usr/bin/env python3
"""
Скрипт запуска миграций Neo4j.

Использование:
    python migrations/run_migrations.py

Миграции выполняются по порядку, уже выполненные пропускаются.
"""

import os
import glob
import sys
from pathlib import Path

# Добавить корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


def get_config():
    """Получить конфигурацию из .env"""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD"),
    }


def get_applied_migrations(session) -> set:
    """Получить список уже выполненных миграций"""
    result = session.run(
        "MATCH (m:Migration) RETURN m.version as version"
    )
    return {record["version"] for record in result}


def parse_migration_version(filepath: str) -> int:
    """Извлечь версию из имени файла: 001_xxx.cypher → 1"""
    filename = os.path.basename(filepath)
    version_str = filename.split('_')[0]
    return int(version_str)


def apply_migration(session, filepath: str, version: int):
    """Применить одну миграцию"""
    print(f"📦 Applying migration {version}: {os.path.basename(filepath)}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        cypher = f.read()
    
    # Разбить на отдельные команды (по ;)
    # Но быть осторожным с ; внутри строк
    commands = []
    current_command = []
    
    for line in cypher.split('\n'):
        line = line.strip()
        
        # Пропустить комментарии
        if line.startswith('//'):
            continue
        
        current_command.append(line)
        
        # Если строка заканчивается на ; — это конец команды
        if line.endswith(';'):
            cmd = '\n'.join(current_command)
            if cmd.strip() and cmd.strip() != ';':
                commands.append(cmd)
            current_command = []
    
    # Выполнить команды
    for i, cmd in enumerate(commands):
        try:
            session.run(cmd)
        except Exception as e:
            print(f"  ❌ Error in command {i+1}: {e}")
            print(f"     Command: {cmd[:100]}...")
            raise
    
    print(f"  ✅ Migration {version} applied successfully")


def main():
    config = get_config()
    
    if not config["password"]:
        print("❌ NEO4J_PASSWORD not set in .env")
        print("   Copy .env.example to .env and fill in values")
        return 1
    
    # Подключение к Neo4j
    print(f"🔌 Connecting to Neo4j at {config['uri']}...")
    
    try:
        driver = GraphDatabase.driver(
            config["uri"],
            auth=(config["user"], config["password"])
        )
        
        with driver.session() as session:
            # Проверить подключение
            session.run("RETURN 1")
            print("✅ Connected to Neo4j")
            
            # Получить выполненные миграции
            applied = get_applied_migrations(session)
            print(f"📋 Already applied: {sorted(applied) if applied else 'none'}")
            
            # Найти все файлы миграций
            migrations_dir = Path(__file__).parent
            migration_files = sorted(glob.glob(str(migrations_dir / "*.cypher")))
            
            if not migration_files:
                print("⚠️  No migration files found")
                return 0
            
            # Применить миграции
            applied_count = 0
            for filepath in migration_files:
                version = parse_migration_version(filepath)
                
                if version in applied:
                    print(f"⏭️  Migration {version} already applied, skipping")
                else:
                    apply_migration(session, filepath, version)
                    applied_count += 1
            
            print()
            if applied_count > 0:
                print(f"🎉 Applied {applied_count} migration(s)")
            else:
                print("✅ All migrations already applied")
            
            return 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        if 'driver' in locals():
            driver.close()


if __name__ == "__main__":
    sys.exit(main())
