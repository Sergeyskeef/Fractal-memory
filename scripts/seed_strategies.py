"""
Скрипт для добавления начальных стратегий в ReasoningBank.

Используется для "посева" данных перед тестированием.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Добавляем корень проекта в путь
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Загружаем переменные окружения
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from src.core.memory import FractalMemory
from src.core.reasoning import ReasoningBank


async def seed_strategies():
    """Добавить начальные стратегии в базу."""
    print("=" * 60)
    print("🌱 SEEDING STRATEGIES")
    print("=" * 60)
    
    # Конфигурация
    config = {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "user_id": os.getenv("USER_ID", "sergey"),
    }
    
    print(f"\n📋 Configuration:")
    print(f"   User ID: {config['user_id']}")
    print(f"   Neo4j URI: {config['neo4j_uri']}")
    
    memory = FractalMemory(config)
    
    try:
        await memory.initialize()
        print("✅ FractalMemory initialized")
        
        # Инициализируем ReasoningBank
        bank = ReasoningBank(memory.graphiti, config["user_id"])
        print("✅ ReasoningBank initialized")
        
        # Стратегии для добавления
        strategies_to_add = [
            {
                "task_type": "coding",
                "description": "Always write pseudocode before implementation",
                "initial_confidence": 0.95,
                "initial_success": True,
            },
            {
                "task_type": "coding",
                "description": "Break complex problems into smaller subproblems (Divide and Conquer)",
                "initial_confidence": 0.90,
                "initial_success": True,
            },
            {
                "task_type": "explanation",
                "description": "Start with a simple example, then explain the general case",
                "initial_confidence": 0.85,
                "initial_success": True,
            },
            {
                "task_type": "generation",
                "description": "Use templates and patterns from similar successful cases",
                "initial_confidence": 0.88,
                "initial_success": True,
            },
        ]
        
        print(f"\n📝 Adding {len(strategies_to_add)} strategies...")
        
        added_count = 0
        for strategy in strategies_to_add:
            try:
                # Проверяем, существует ли уже такая стратегия
                existing = await bank.get_strategies(
                    task_type=strategy["task_type"],
                    limit=10
                )
                
                # Проверяем по описанию
                exists = any(
                    s.description == strategy["description"]
                    for s in existing
                )
                
                if exists:
                    print(f"   ⏭️  Strategy already exists: {strategy['description'][:50]}...")
                    continue
                
                # Добавляем стратегию
                strategy_id = await bank.add_strategy(
                    task_type=strategy["task_type"],
                    description=strategy["description"],
                    initial_success=strategy["initial_success"],
                )
                
                print(f"   ✅ Added: {strategy['task_type']} -> {strategy['description'][:60]}...")
                print(f"      ID: {strategy_id[:8]}..., Confidence: {strategy['initial_confidence']}")
                added_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to add strategy: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n✅ Successfully added {added_count} strategies")
        
        # Проверяем результат
        print(f"\n🔍 Verifying strategies in database...")
        for task_type in ["coding", "explanation", "generation"]:
            strategies = await bank.get_strategies(task_type=task_type, limit=5)
            print(f"   {task_type}: {len(strategies)} strategies")
            for s in strategies[:2]:
                print(f"      - {s.description[:50]}... (confidence: {s.success_rate or 0.0:.2f})")
        
        print("\n" + "=" * 60)
        print("🎉 SEEDING COMPLETE")
        print("=" * 60)
        print("✅ Strategies are ready for use in prompts")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await memory.close()
        print("\n🧹 Cleaned up")


if __name__ == "__main__":
    asyncio.run(seed_strategies())

