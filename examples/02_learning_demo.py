#!/usr/bin/env python3
"""
02. Демонстрация самообучения (ReasoningBank)

Демонстрирует:
- Логирование опыта (success/failure)
- Извлечение стратегий из опыта
- Выбор стратегии для новой задачи
- Обновление confidence на основе результатов

Использование:
    python examples/02_learning_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def main():
    """Пример использования ReasoningBank"""

    print("=" * 60)
    print("  FRACTAL MEMORY - Learning Example")
    print("=" * 60)
    print()

    # TODO: Раскомментировать после реализации
    # from src.core.learning import ReasoningBank, Outcome
    # from src.core.graphiti_adapter import GraphitiAdapter

    print("⚠️  NOTE: This is a template example.")
    print("    Uncomment imports after implementing src/core/learning.py")
    print()

    # ═══════════════════════════════════════════════════════════
    # 1. КОНФИГУРАЦИЯ
    # ═══════════════════════════════════════════════════════════

    config = {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
    }

    # TODO: Раскомментировать после реализации
    # graph = GraphitiAdapter(config)
    # await graph.initialize()
    #
    # bank = ReasoningBank(graph, {
    #     "min_experiences_for_strategy": 3,
    #     "exploration_rate": 0.1
    # })

    print("✓ Configuration loaded")
    print()

    # ═══════════════════════════════════════════════════════════
    # 2. ЛОГИРОВАНИЕ УСПЕШНОГО ОПЫТА
    # ═══════════════════════════════════════════════════════════

    print("📝 Logging successful experiences...")
    print()

    # Пример: агент успешно выполнил задачи используя определенный подход
    successful_experiences = [
        {
            "task": "Debug Python TypeError",
            "action": "Check type hints and add explicit type casting",
            "reasoning": "Type errors usually caused by implicit conversions",
        },
        {
            "task": "Optimize database query",
            "action": "Add index on frequently queried column",
            "reasoning": "Slow queries often due to missing indexes",
        },
        {
            "task": "Fix async deadlock",
            "action": "Use asyncio.gather() instead of nested awaits",
            "reasoning": "Nested awaits can cause blocking",
        },
    ]

    # TODO: Раскомментировать после реализации
    # for exp in successful_experiences:
    #     exp_id = await bank.log_experience(
    #         task_description=exp["task"],
    #         task_type="debugging",
    #         context={},
    #         action_taken=exp["action"],
    #         outcome=Outcome.SUCCESS,
    #         reasoning=exp["reasoning"]
    #     )
    #     print(f"  ✓ Logged: {exp['task']}")

    for exp in successful_experiences:
        print(f"  Would log: {exp['task']}")

    print()

    # ═══════════════════════════════════════════════════════════
    # 3. ЛОГИРОВАНИЕ НЕУДАЧНОГО ОПЫТА
    # ═══════════════════════════════════════════════════════════

    print("📝 Logging failed experiences...")
    print()

    failed_experiences = [
        {
            "task": "Fix memory leak",
            "action": "Restart service",
            "reasoning": "Thought restart would help",
            "lesson": "Need to find root cause, not just restart",
        },
    ]

    # TODO: Раскомментировать после реализации
    # for exp in failed_experiences:
    #     exp_id = await bank.log_experience(
    #         task_description=exp["task"],
    #         task_type="debugging",
    #         context={},
    #         action_taken=exp["action"],
    #         outcome=Outcome.FAILURE,
    #         reasoning=exp["lesson"]
    #     )
    #     print(f"  ✗ Logged failure: {exp['task']}")

    for exp in failed_experiences:
        print(f"  Would log failure: {exp['task']}")

    print()

    # ═══════════════════════════════════════════════════════════
    # 4. ИЗВЛЕЧЕНИЕ СТРАТЕГИЙ
    # ═══════════════════════════════════════════════════════════

    print("🧠 Extracting strategies from experience...")
    print()

    # TODO: Раскомментировать после реализации
    # strategies = await bank.extract_strategies()
    #
    # if strategies:
    #     print(f"✓ Extracted {len(strategies)} strategies:")
    #     for s in strategies:
    #         print(f"  - {s.description}")
    #         print(f"    Success rate: {s.confidence:.2%}")
    #         print(f"    Applicable to: {', '.join(s.applicable_contexts)}")
    #         print()
    # else:
    #     print("  No strategies extracted yet (need more experiences)")

    print("  Would extract strategies like:")
    print("    - 'Check type hints for TypeError bugs' (confidence: 95%)")
    print("    - 'Add database indexes for slow queries' (confidence: 90%)")
    print()

    # ═══════════════════════════════════════════════════════════
    # 5. ПОЛУЧЕНИЕ РЕКОМЕНДАЦИИ ДЛЯ НОВОЙ ЗАДАЧИ
    # ═══════════════════════════════════════════════════════════

    print("🎯 Getting strategy recommendation for new task...")
    print()

    new_task = {
        "description": "Application crashes with TypeError on user input",
        "type": "debugging",
        "context": {"error_type": "TypeError", "component": "input_validation"},
    }

    print(f"  Task: {new_task['description']}")
    print()

    # TODO: Раскомментировать после реализации
    # recommended = await bank.get_strategies_for_task(
    #     task_description=new_task['description'],
    #     task_type=new_task['type'],
    #     context=new_task['context']
    # )
    #
    # if recommended:
    #     best = recommended[0]
    #     print(f"  Recommended strategy:")
    #     print(f"    {best.description}")
    #     print(f"    Confidence: {best.confidence:.2%}")
    #     print(f"    Based on {best.success_count} successful applications")
    # else:
    #     print("  No matching strategies found (will explore)")

    print("  Would recommend: 'Check type hints and add type casting'")
    print("    (based on similar past successes)")
    print()

    # ═══════════════════════════════════════════════════════════
    # 6. СИМУЛЯЦИЯ ПРИМЕНЕНИЯ И ОБНОВЛЕНИЯ
    # ═══════════════════════════════════════════════════════════

    print("🔄 Applying strategy and updating based on result...")
    print()

    # Агент применяет стратегию и она работает
    # TODO: Раскомментировать после реализации
    # if recommended:
    #     strategy_id = recommended[0].id
    #     await bank.update_strategy_feedback(
    #         strategy_id=strategy_id,
    #         outcome=Outcome.SUCCESS
    #     )
    #     print(f"  ✓ Strategy worked! Confidence increased")
    # else:
    #     print("  No strategy to update")

    print("  Strategy applied successfully")
    print("  Confidence updated: 95% → 96%")
    print()

    # ═══════════════════════════════════════════════════════════
    # 7. СТАТИСТИКА ОБУЧЕНИЯ
    # ═══════════════════════════════════════════════════════════

    print("📊 Learning Statistics:")
    print()

    # TODO: Раскомментировать после реализации
    # stats = await bank.get_learning_stats()
    # print(f"  Total experiences: {stats['total_experiences']}")
    # print(f"  Successful: {stats['successful']}")
    # print(f"  Failed: {stats['failed']}")
    # print(f"  Strategies extracted: {stats['strategies_count']}")
    # print(f"  Avg confidence: {stats['avg_confidence']:.2%}")

    print("  Total experiences: 4")
    print("  Successful: 3")
    print("  Failed: 1")
    print("  Strategies extracted: 2")
    print("  Avg confidence: 92%")
    print()

    # TODO: Раскомментировать после реализации
    # await graph.close()

    print("=" * 60)
    print("✅ Learning example complete!")
    print()
    print("Key concepts demonstrated:")
    print("  - Logging success/failure experiences")
    print("  - Automatic strategy extraction")
    print("  - Strategy recommendation for similar tasks")
    print("  - Confidence updates based on outcomes")
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
