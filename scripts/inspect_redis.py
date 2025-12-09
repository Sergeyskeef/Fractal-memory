#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
Redis Inspector - Исследование Redis для L0/L1
═══════════════════════════════════════════════════════
"""

import os
import sys
import asyncio
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed")

try:
    import redis.asyncio as redis
except ImportError:
    print("❌ redis not installed. Install with: pip install redis")
    sys.exit(1)


async def inspect_redis():
    """Исследовать Redis."""
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    print("=" * 70)
    print("🔍 REDIS INSPECTOR")
    print("=" * 70)
    print(f"📡 Connecting to: {redis_url}")
    print()
    
    client = await redis.from_url(redis_url)
    
    try:
        # Проверить подключение
        await client.ping()
        print("✅ Connected to Redis")
        print()
        
        # Получить все ключи
        print("🔑 ALL KEYS:")
        print("-" * 70)
        
        keys = await client.keys('*')
        
        if keys:
            print(f"Found {len(keys)} keys")
            print()
            
            # Группировать по префиксам
            prefixes = {}
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                prefix = key_str.split(':')[0] if ':' in key_str else 'no_prefix'
                
                if prefix not in prefixes:
                    prefixes[prefix] = []
                prefixes[prefix].append(key_str)
            
            # Показать по префиксам
            for prefix, prefix_keys in sorted(prefixes.items()):
                print(f"\n  Prefix: {prefix} ({len(prefix_keys)} keys)")
                for key in prefix_keys[:10]:  # Первые 10
                    print(f"    - {key}")
                if len(prefix_keys) > 10:
                    print(f"    ... and {len(prefix_keys) - 10} more")
            
            print()
            
            # Показать примеры данных
            print("📦 KEY EXAMPLES:")
            print("-" * 70)
            
            for key in keys[:5]:  # Первые 5 ключей
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                # Определить тип
                key_type = await client.type(key)
                key_type_str = key_type.decode('utf-8') if isinstance(key_type, bytes) else key_type
                
                print(f"\n  Key: {key_str}")
                print(f"  Type: {key_type_str}")
                
                # Получить значение в зависимости от типа
                if key_type_str == 'string':
                    value = await client.get(key)
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    if len(value_str) > 200:
                        value_str = value_str[:200] + "..."
                    print(f"  Value: {value_str}")
                
                elif key_type_str == 'hash':
                    value = await client.hgetall(key)
                    print(f"  Fields: {len(value)}")
                    for field, val in list(value.items())[:5]:
                        field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                        val_str = val.decode('utf-8') if isinstance(val, bytes) else str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        print(f"    - {field_str}: {val_str}")
                
                elif key_type_str == 'list':
                    length = await client.llen(key)
                    print(f"  Length: {length}")
                    items = await client.lrange(key, 0, 4)
                    for item in items:
                        item_str = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                        if len(item_str) > 100:
                            item_str = item_str[:100] + "..."
                        print(f"    - {item_str}")
                
                elif key_type_str == 'set':
                    size = await client.scard(key)
                    print(f"  Size: {size}")
                    members = await client.smembers(key)
                    for member in list(members)[:5]:
                        member_str = member.decode('utf-8') if isinstance(member, bytes) else str(member)
                        print(f"    - {member_str}")
                
                elif key_type_str == 'zset':
                    size = await client.zcard(key)
                    print(f"  Size: {size}")
                    members = await client.zrange(key, 0, 4, withscores=True)
                    for member, score in members:
                        member_str = member.decode('utf-8') if isinstance(member, bytes) else str(member)
                        print(f"    - {member_str}: {score}")
            
            print()
            
            # Поиск L0/L1 ключей
            print("🔍 SEARCHING FOR L0/L1 KEYS:")
            print("-" * 70)
            
            patterns = ['l0:*', 'l1:*', 'L0:*', 'L1:*', '*episodic*', '*short*', '*memory*']
            
            for pattern in patterns:
                matches = await client.keys(pattern)
                if matches:
                    print(f"\n  Pattern '{pattern}': {len(matches)} matches")
                    for match in matches[:5]:
                        match_str = match.decode('utf-8') if isinstance(match, bytes) else match
                        print(f"    - {match_str}")
                else:
                    print(f"\n  Pattern '{pattern}': No matches")
        
        else:
            print("  ⚠️  No keys found in Redis")
        
        print()
        print("=" * 70)
        print("✅ Redis inspection complete!")
        print("=" * 70)
    
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(inspect_redis())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
