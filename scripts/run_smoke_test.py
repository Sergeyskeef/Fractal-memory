"""
Run full smoke test: optional reset, conversation simulation, forensic inspect.

Usage:
    python3 scripts/run_smoke_test.py          # no reset
    python3 scripts/run_smoke_test.py --reset  # reset then run
"""

import asyncio
import os
import sys
import argparse
from typing import List

import httpx
from dotenv import load_dotenv


MESSAGES: List[str] = [
    "Привет, Марк. Начинаем тест памяти.",
    "Меня зовут Сергей, я живу в Москве.",
    "Мы строим проект 'Фрактальная Память'.",
    "Запоминай архитектуру: L0 - это рабочая память в Redis, сырые логи.",
    "L1 - это эпизодическая память. Там хранятся саммари диалогов.",
    "L2 - это граф знаний в Neo4j, он хранит долговременные эпизоды.",
    "Еще у нас есть Reasoning Bank для хранения стратегий.",
    "Кстати, важный факт: я люблю кататься на лонгборде.",
    "Но я не люблю BMX, не путай.",
    "Вернемся к технике. Консолидация происходит каждые 15 сообщений.",
    "Для сжатия текста мы используем GPT-5 Mini.",
    "В L3 у нас лежат Сущности (Entities), которые извлекает Graphiti.",
    "Ты должен использовать этот опыт, чтобы не повторять ошибок.",
    "Теперь расскажи мне, что ты запомнил про L0 и L1?",
    "Отлично. Это пятнадцатое сообщение. Сейчас должен сработать триггер.",
    "А теперь проверь, сохранилось ли все это в долговременную память.",
]


def ensure_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


async def reset_if_needed(do_reset: bool) -> None:
    if not do_reset:
        return
    from scripts.reset_memory import wipe_redis, wipe_neo4j  # type: ignore

    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    await wipe_redis(redis_url)
    await wipe_neo4j(neo4j_uri, neo4j_user, neo4j_password)


async def run_conversation() -> None:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    endpoint = base_url.rstrip("/") + "/chat"
    user_id = os.getenv("USER_ID", "sergey")

    print(f"🌐 Target endpoint: {endpoint} (user_id={user_id})")
    timeout = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for idx, msg in enumerate(MESSAGES, 1):
            print(f"\n👤 User [{idx}/16]: {msg}")
            try:
                resp = await client.post(endpoint, json={"message": msg, "user_id": user_id})
            except Exception as exc:
                print(f"❌ HTTP error on message {idx}: {exc}")
                return

            if resp.status_code != 200:
                print(f"❌ Server returned {resp.status_code}: {resp.text}")
                return

            try:
                data = resp.json()
                reply = data.get("response") or data
            except Exception:
                reply = resp.text

            print(f"🤖 Mark: {str(reply)[:500]}")
            await asyncio.sleep(5.0)  # увеличенная пауза для исключения гонок


async def run_inspect() -> None:
    import scripts.inspect_everything as inspector  # type: ignore

    if hasattr(inspector, "main"):
        await inspector.main()
    else:
        print("⚠️ inspector.main not found")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe Redis and Neo4j before test")
    args = parser.parse_args()

    load_dotenv()
    ensure_path()

    if args.reset:
        print("🔄 Resetting memory (Redis + Neo4j)...")
        await reset_if_needed(True)

    print("🚀 Running conversation simulation...")
    await run_conversation()

    print("\n🔍 Running forensic inspection...")
    await run_inspect()


if __name__ == "__main__":
    asyncio.run(main())
