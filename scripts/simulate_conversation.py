"""
Simulate a 16-turn dialog to trigger L0->L1 consolidation and inspect memory.

Usage:
    python3 scripts/simulate_conversation.py
"""

import asyncio
import os
import sys
from typing import List

import httpx
from dotenv import load_dotenv


def ensure_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


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
    "Для сжатия текста мы используем GPT-5 Nano.",
    "В L3 у нас лежат Сущности (Entities), которые извлекает Graphiti.",
    "Ты должен использовать этот опыт, чтобы не повторять ошибок.",
    "Теперь расскажи мне, что ты запомнил про L0 и L1?",
    "Отлично. Это пятнадцатое сообщение. Сейчас должен сработать триггер.",
    "А теперь проверь, сохранилось ли все это в долговременную память.",
]


async def run_dialog() -> None:
    load_dotenv()
    ensure_path()

    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    endpoint = base_url.rstrip("/") + "/chat"
    user_id = os.getenv("USER_ID", "sergey")

    print(f"🌐 Target endpoint: {endpoint} (user_id={user_id})")
    timeout = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for idx, msg in enumerate(MESSAGES, 1):
            print(f"\n👤 User [{idx}/16]: {msg}")
            try:
                resp = await client.post(
                    endpoint,
                    json={"message": msg, "user_id": user_id},
                )
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
            await asyncio.sleep(1.0)  # небольшая пауза, чтобы не создать гонки

    # Итоговая проверка: запустить deep_inspect_v2
    try:
        import scripts.deep_inspect_v2 as inspector

        if hasattr(inspector, "inspect_l3_mystery"):
            print("\n📊 Running deep_inspect_v2.inspect_l3_mystery() ...")
            await inspector.inspect_l3_mystery()
        else:
            print("⚠️ deep_inspect_v2.inspect_l3_mystery() not found; skipping.")
    except Exception as exc:
        print(f"⚠️ Failed to run deep_inspect_v2: {exc}")


if __name__ == "__main__":
    asyncio.run(run_dialog())
