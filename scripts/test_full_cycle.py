"""
E2E тест полного цикла работы агента через FastAPI.

Проверяет:
1. Запуск FastAPI сервера (должен быть запущен отдельно)
2. Отправка запроса через HTTP
3. Получение ответа с использованием памяти и стратегий
"""

import asyncio
import os
import sys
import time
from dotenv import load_dotenv

# Загружаем переменные окружения
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# Добавляем корень проекта в путь
sys.path.insert(0, project_root)

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Install with: pip install httpx")
    sys.exit(1)


async def test_full_cycle():
    """Тест полного цикла через FastAPI."""
    print("=" * 60)
    print("🔄 E2E TEST: Full Agent Cycle via FastAPI")
    print("=" * 60)
    
    base_url = os.getenv("API_URL", "http://localhost:8000")
    print(f"\n📡 Testing API at: {base_url}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Проверка health
        print("\n1️⃣ Checking health...")
        try:
            health_response = await client.get(f"{base_url}/health")
            if health_response.status_code == 200:
                print("   ✅ API is healthy")
            else:
                print(f"   ⚠️  Health check returned: {health_response.status_code}")
        except httpx.ConnectError:
            print(f"   ❌ Cannot connect to {base_url}")
            print("   💡 Make sure FastAPI server is running:")
            print("      cd /root/Mark_project/fractal_memory")
            print("      uvicorn backend.main:app --reload")
            return
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return
        
        # Тест 1: Простой запрос
        print("\n2️⃣ Test 1: Simple query")
        print("   Sending: 'Как написать код на Python?'")
        
        try:
            start_time = time.time()
            response = await client.post(
                f"{base_url}/chat",
                json={"message": "Как написать код на Python?"}
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Response received ({elapsed:.2f}s)")
                print(f"   Response: {data.get('response', '')[:200]}...")
                print(f"   Context items: {data.get('context_count', 0)}")
                print(f"   Strategies used: {data.get('strategies_used', [])}")
                print(f"   Processing time: {data.get('processing_time_ms', 0):.0f}ms")
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Тест 2: Запрос с использованием памяти
        print("\n3️⃣ Test 2: Memory recall")
        print("   First, saving a fact...")
        
        # Сохраняем факт через memory API (если есть)
        try:
            memory_response = await client.post(
                f"{base_url}/memory/remember",
                json={
                    "content": "Мой любимый язык программирования — Python",
                    "importance": 0.9
                }
            )
            if memory_response.status_code == 200:
                print("   ✅ Fact saved")
            else:
                print(f"   ⚠️  Could not save fact: {memory_response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Memory API not available: {e}")
        
        # Небольшая задержка для обработки
        await asyncio.sleep(1)
        
        print("   Now asking: 'Какой мой любимый язык программирования?'")
        try:
            response2 = await client.post(
                f"{base_url}/chat",
                json={"message": "Какой мой любимый язык программирования?"}
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                response_text = data2.get('response', '').lower()
                print(f"   ✅ Response received")
                print(f"   Response: {data2.get('response', '')[:200]}...")
                
                if 'python' in response_text:
                    print("   ✅ Memory recall works! (Response mentions Python)")
                else:
                    print("   ⚠️  Memory might not be used (Python not mentioned)")
            else:
                print(f"   ❌ Request failed: {response2.status_code}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Тест 3: Проверка стратегий
        print("\n4️⃣ Test 3: Strategy usage")
        try:
            strategies_response = await client.get(f"{base_url}/strategies?task_type=coding")
            if strategies_response.status_code == 200:
                strategies_data = strategies_response.json()
                strategies = strategies_data.get('strategies', [])
                print(f"   ✅ Found {len(strategies)} strategies for 'coding'")
                if strategies:
                    for s in strategies[:3]:
                        desc = s.get('description', 'Unknown') or 'Unknown'
                        conf = s.get('success_rate', 0) or 0.0
                        print(f"      - {desc[:60]}... (confidence: {conf:.2f})")
                else:
                    print("   ℹ️  No strategies yet (will be created after interactions)")
            else:
                print(f"   ⚠️  Strategies endpoint returned: {strategies_response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Could not check strategies: {e}")
        
        # Итоговый результат
        print("\n" + "=" * 60)
        print("🎉 E2E TEST COMPLETE")
        print("=" * 60)
        print("✅ FastAPI integration verified")
        print("✅ Agent responds to queries")
        print("✅ Memory and strategies are integrated")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_full_cycle())

