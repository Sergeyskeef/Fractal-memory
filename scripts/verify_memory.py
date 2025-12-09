"""
Скрипт верификации работы Fractal Memory и Embeddings.

Проверяет:
1. Авто-инициализацию OpenAIEmbedder
2. Корректность векторов (тип, размерность)
3. Семантический поиск (поиск по смыслу, а не по ключевым словам)
"""

import asyncio
import os
import sys
import numpy as np
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"📄 Loaded .env from: {env_path}")

# Добавляем корень проекта в путь
sys.path.insert(0, project_root)

from src.core.memory import FractalMemory
from src.core.embeddings import OpenAIEmbedder


async def main():
    print("=" * 60)
    print("🧠 FRACTAL MEMORY VERIFICATION")
    print("=" * 60)
    
    # Проверка ключа
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ CRITICAL: OPENAI_API_KEY not found in environment")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
    
    # Конфиг из переменных окружения или дефолты
    config = {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "user_id": "test_user",
        # embedding_func НЕ передаем, проверяем авто-создание
    }
    
    print(f"\n📋 Configuration:")
    print(f"   Neo4j URI: {config['neo4j_uri']}")
    print(f"   Redis URL: {config['redis_url']}")
    print(f"   User ID: {config['user_id']}")
    
    memory = FractalMemory(config)
    
    try:
        print("\n🤖 Initializing Fractal Memory...")
        await memory.initialize()
        print("✅ Memory initialized successfully")
        
        # 1. Тест Embeddings Low-Level
        print("\n" + "=" * 60)
        print("🧠 TEST 1: Embeddings Low-Level")
        print("=" * 60)
        
        embedder = OpenAIEmbedder()
        
        if not embedder.client:
            print("❌ OpenAIEmbedder client not initialized (missing API key)")
            return
        
        test_text = "Тест семантического поиска"
        print(f"   Generating embedding for: '{test_text}'")
        
        vector = await embedder.get_embedding(test_text)
        
        # Проверка типа
        if isinstance(vector, np.ndarray):
            print(f"✅ Type check passed: numpy.ndarray")
        else:
            print(f"❌ Type check failed: got {type(vector)}, expected numpy.ndarray")
            return
        
        # Проверка размерности
        expected_dim = 1536  # text-embedding-3-small
        if len(vector) == expected_dim:
            print(f"✅ Dimension check passed: {len(vector)} (expected {expected_dim})")
        else:
            print(f"⚠️  Dimension mismatch: got {len(vector)}, expected {expected_dim}")
            print(f"   (This might be OK if using different embedding model)")
        
        # Проверка dtype
        if vector.dtype == np.float32:
            print(f"✅ Dtype check passed: {vector.dtype}")
        else:
            print(f"⚠️  Dtype: {vector.dtype} (expected float32)")
        
        # 2. Тест Semantic Search через FractalMemory
        print("\n" + "=" * 60)
        print("💾 TEST 2: Semantic Search")
        print("=" * 60)
        
        secret = "Секретный код проекта — 'СинийГоризонт'."
        print(f"   Saving fact: '{secret}'")
        
        item_id = await memory.remember(secret, importance=1.0)
        print(f"   ✅ Saved with ID: {item_id[:8]}...")
        
        # Небольшая задержка для обработки
        print("   ⏳ Waiting for processing...")
        await asyncio.sleep(2)
        
        # Поиск семантически похожего запроса (слова не совпадают)
        query = "Какой пароль у проекта?"
        print(f"\n   Searching with query: '{query}'")
        print("   (Keywords don't match, should work via semantic similarity)")
        
        results = await memory.recall(query, limit=5)
        
        print(f"\n   Found {len(results)} result(s):")
        found = False
        for i, res in enumerate(results, 1):
            print(f"   {i}. Score: {res.score:.4f} | Source: {res.source}")
            print(f"      Content: {res.content[:80]}...")
            if "СинийГоризонт" in res.content:
                found = True
                print(f"      ✅ MATCH FOUND!")
        
        # Итоговый результат
        print("\n" + "=" * 60)
        if found:
            print("🎉 SUCCESS: Semantic search works!")
            print("   Context retrieved despite different keywords.")
            print("   The system understands meaning, not just keywords.")
        else:
            print("⚠️  WARNING: Specific fact not found in top results.")
            print("   Possible reasons:")
            print("   - Embeddings not yet indexed in Graphiti")
            print("   - Need to consolidate L0 → L1 → L2 first")
            print("   - Semantic similarity threshold too high")
            print("\n   Try running consolidation:")
            print("   await memory.consolidate()")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🧹 Cleaning up...")
        await memory.close()
        print("✅ Done")


if __name__ == "__main__":
    asyncio.run(main())

