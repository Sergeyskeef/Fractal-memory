#!/usr/bin/env python3
"""
01. Базовое использование Fractal Memory

Демонстрирует:
- Инициализацию FractalMemory
- Сохранение информации (remember)
- Извлечение информации (recall)
- Консолидацию между уровнями памяти

Требования:
- Docker контейнеры запущены (make docker-up)
- Миграции выполнены (make migrate)
- .env файл настроен

Использование:
    python examples/01_basic_usage.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавить src в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv()


async def main():
    """Основной пример использования"""

    print("=" * 60)
    print("  FRACTAL MEMORY - Basic Usage Example")
    print("=" * 60)
    print()

    # ═══════════════════════════════════════════════════════════
    # 1. ИМПОРТ (после реализации кода)
    # ═══════════════════════════════════════════════════════════

    # TODO: Раскомментировать после реализации FractalMemory
    # from src.core.memory import FractalMemory

    # Временная заглушка для демонстрации
    print("⚠️  NOTE: This is a template example.")
    print("    Uncomment imports after implementing src/core/memory.py")
    print()

    # ═══════════════════════════════════════════════════════════
    # 2. КОНФИГУРАЦИЯ
    # ═══════════════════════════════════════════════════════════

    config = {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        # Настройки памяти
        "l0_capacity": 10,  # Working memory
        "l1_capacity": 50,  # Short-term memory
        "importance_threshold": 0.3,  # Порог для консолидации
    }

    print("✓ Configuration loaded")
    print(f"  Neo4j: {config['neo4j_uri']}")
    print(f"  Redis: {config['redis_url']}")
    print()

    # ═══════════════════════════════════════════════════════════
    # 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
    # ═══════════════════════════════════════════════════════════

    # TODO: Раскомментировать после реализации
    # memory = FractalMemory(config)
    # await memory.initialize()
    # print("✓ Fractal Memory initialized")
    # print()

    # ═══════════════════════════════════════════════════════════
    # 4. СОХРАНЕНИЕ ИНФОРМАЦИИ (remember)
    # ═══════════════════════════════════════════════════════════

    print("📝 Saving information to memory...")
    print()

    # Примеры данных для сохранения
    memories = [
        "User prefers Python over JavaScript",
        "User is working on an AI memory system project called Fractal Memory",
        "User uses Neo4j as graph database and Redis for event bus",
        "User mentioned they want to reduce LLM token usage by 90%",
        "User asked about Graphiti library compatibility",
    ]

    # TODO: Раскомментировать после реализации
    # for idx, content in enumerate(memories, 1):
    #     await memory.remember(content, importance_score=0.8)
    #     print(f"  {idx}. Saved: {content[:50]}...")
    #
    # print()
    # print(f"✓ Saved {len(memories)} memories to L0 (working memory)")
    # print()

    # Заглушка для демонстрации
    for idx, content in enumerate(memories, 1):
        print(f"  {idx}. Would save: {content[:50]}...")
    print()

    # ═══════════════════════════════════════════════════════════
    # 5. КОНСОЛИДАЦИЯ (L0 → L1 → L2/L3)
    # ═══════════════════════════════════════════════════════════

    print("🔄 Consolidating memory...")
    print()

    # TODO: Раскомментировать после реализации
    # stats = await memory.consolidate()
    # print(f"✓ Consolidation complete:")
    # print(f"  L0 → L1: {stats['l0_to_l1']} items")
    # print(f"  L1 → L2: {stats['l1_to_l2']} items")
    # print()

    # Заглушка
    print("  Would consolidate memories across levels")
    print()

    # ═══════════════════════════════════════════════════════════
    # 6. ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ (recall)
    # ═══════════════════════════════════════════════════════════

    print("🔍 Querying memory...")
    print()

    queries = [
        "What programming language does the user prefer?",
        "What databases is the user using?",
        "What are the user's project goals?",
    ]

    for idx, query in enumerate(queries, 1):
        print(f"  Query {idx}: {query}")

        # TODO: Раскомментировать после реализации
        # results = await memory.recall(query, top_k=3)
        #
        # if results:
        #     print(f"  Found {len(results)} relevant memories:")
        #     for r in results[:2]:
        #         print(f"    - {r.content[:60]}...")
        #         print(f"      (relevance: {r.relevance_score:.2f})")
        # else:
        #     print("    No relevant memories found")
        #
        # print()

        # Заглушка
        print(f"    Would search for: {query}")
        print()

    # ═══════════════════════════════════════════════════════════
    # 7. СТАТИСТИКА ПАМЯТИ
    # ═══════════════════════════════════════════════════════════

    print("📊 Memory Statistics:")
    print()

    # TODO: Раскомментировать после реализации
    # stats = memory.get_stats()
    # print(f"  L0 (Working):    {stats['l0_count']}/{stats['l0_capacity']}")
    # print(f"  L1 (Short-term): {stats['l1_count']}/{stats['l1_capacity']}")
    # print(f"  L2 (Episodes):   {stats['l2_count']}")
    # print(f"  L3 (Long-term):  {stats['l3_count']}")
    # print(f"  Total memories:  {stats['total']}")
    # print()

    # Заглушка
    print("  L0 (Working):    5/10")
    print("  L1 (Short-term): 3/50")
    print("  L2 (Episodes):   0")
    print("  L3 (Long-term):  0")
    print()

    # ═══════════════════════════════════════════════════════════
    # 8. CLEANUP
    # ═══════════════════════════════════════════════════════════

    # TODO: Раскомментировать после реализации
    # await memory.close()
    # print("✓ Memory closed")

    print("=" * 60)
    print("✅ Example complete!")
    print()
    print("Next steps:")
    print("  1. Implement src/core/memory.py (see docs/03_PHASE2_MEMORY.md)")
    print("  2. Uncomment code in this example")
    print("  3. Run: python examples/01_basic_usage.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
