"""Chat router."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.agent import FractalAgent
from backend.models import ChatMessage

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None  # Опционально, если не указан - используется из конфига


class ChatResponse(BaseModel):
    response: str
    context_count: int
    strategies_used: List[str] = []
    processing_time_ms: float = 0.0


def get_agent_from_main():
    """Получить агента из main модуля."""
    from backend.main import agent
    if agent is None:
        raise HTTPException(503, "Agent not initialized")
    return agent


@router.get("/history", response_model=List[ChatMessage])
async def get_history(
    limit: int = 50,
    agent: FractalAgent = Depends(get_agent_from_main)
):
    """
    Получить историю чата из памяти (L0/L1).
    
    Args:
        limit: Максимальное количество сообщений
        agent: Экземпляр FractalAgent
    
    Returns:
        Список сообщений в формате для фронтенда:
        [
          {
            "id": str,
            "role": "user" | "assistant",
            "content": str,
            "timestamp": str (ISO datetime),
            "metadata": {...}
          },
          ...
        ]
    """
    messages = []
    
    try:
        # Получаем последние сообщения из L0 (рабочая память)
        if hasattr(agent.memory, 'redis_store'):
            l0_items = await agent.memory.redis_store.l0_get_recent(limit)
            
            for item in l0_items:
                content = item.get("content", "")
                
                # Парсим timestamp
                timestamp_str = item.get("timestamp", "")
                try:
                    if isinstance(timestamp_str, str):
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.now()
                except:
                    timestamp = datetime.now()
                
                # Проверяем, содержит ли контент пару сообщений
                # Формат сохранения: "User: текст\nAssistant: текст" или просто "текст\nAssistant: текст"
                # Если есть "\nAssistant:" - это пара сообщений
                if "\nAssistant:" in content:
                    # Разделяем на отдельные сообщения
                    parts = content.split("\nAssistant:", 1)
                    
                    if len(parts) == 2:
                        # Первая часть - сообщение пользователя
                        user_content = parts[0]
                        # Убираем префикс "User:" если есть
                        if user_content.startswith("User:"):
                            user_content = user_content[5:].strip()
                        else:
                            user_content = user_content.strip()
                        
                        # Вторая часть - ответ ассистента (уже без префикса после split)
                        assistant_content = parts[1].strip()
                        
                        # Получаем stream_id для правильной сортировки
                        stream_id = item.get('stream_id', '0-0')
                        
                        # Добавляем сообщение пользователя (если есть контент)
                        if user_content:
                            messages.append({
                                "id": f"{stream_id}_user",
                                "role": "user",
                                "content": user_content,
                                "timestamp": timestamp.isoformat(),
                                "stream_id": stream_id,  # Сохраняем для сортировки
                                "metadata": {
                                    "importance": item.get("importance", 0.5),
                                    "context_count": 0,
                                }
                            })
                        
                        # Добавляем ответ ассистента (если есть контент)
                        # Assistant сообщение должно быть после user
                        # Используем оригинальный timestamp, но при сортировке user будет первым
                        if assistant_content:
                            messages.append({
                                "id": f"{stream_id}_assistant",
                                "role": "assistant",
                                "content": assistant_content,
                                "timestamp": timestamp.isoformat(),  # Оставляем тот же timestamp
                                "stream_id": stream_id,  # Сохраняем для сортировки
                                "metadata": {
                                    "importance": item.get("importance", 0.5),
                                    "context_count": 0,
                                }
                            })
                        # Переходим к следующему item, так как мы уже обработали этот
                        continue
                    else:
                        # Если разделение не сработало, пробуем как одно сообщение
                        role = "user" if content.startswith("User:") else "assistant"
                        clean_content = content.replace("User:", "").replace("Assistant:", "").strip()
                        if clean_content:
                            messages.append({
                                "id": item.get("stream_id", f"msg_{len(messages)}"),
                                "role": role,
                                "content": clean_content,
                                "timestamp": timestamp.isoformat(),
                                "metadata": {
                                    "importance": item.get("importance", 0.5),
                                    "context_count": 0,
                                }
                            })
                elif "Assistant:" in content and not content.startswith("Assistant:"):
                    # Если есть "Assistant:" но не в начале и нет \n - пробуем разделить
                    parts = content.split("Assistant:", 1)
                    if len(parts) == 2:
                        user_content = parts[0].replace("User:", "").strip()
                        assistant_content = parts[1].strip()
                        
                        stream_id = item.get('stream_id', '0-0')
                        
                        if user_content:
                            messages.append({
                                "id": f"{stream_id}_user",
                                "role": "user",
                                "content": user_content,
                                "timestamp": timestamp.isoformat(),
                                "stream_id": stream_id,
                                "metadata": {
                                    "importance": item.get("importance", 0.5),
                                    "context_count": 0,
                                }
                            })
                        if assistant_content:
                            # Assistant сообщение должно быть после user
                            # Используем оригинальный timestamp, сортировка по роли обеспечит правильный порядок
                            messages.append({
                                "id": f"{stream_id}_assistant",
                                "role": "assistant",
                                "content": assistant_content,
                                "timestamp": timestamp.isoformat(),
                                "stream_id": stream_id,
                                "metadata": {
                                    "importance": item.get("importance", 0.5),
                                    "context_count": 0,
                                }
                            })
                else:
                    # Одно сообщение - определяем роль
                    role = item.get("role", "user" if "User:" in content else "assistant")
                    
                    # Извлекаем чистый текст (убираем префикс "User:" или "Assistant:")
                    if content.startswith("User:"):
                        content = content[5:].strip()
                        role = "user"
                    elif content.startswith("Assistant:"):
                        content = content[10:].strip()
                        role = "assistant"
                    
                    if content:  # Добавляем только если есть контент
                        stream_id = item.get("stream_id", f"0-{len(messages)}")
                        messages.append({
                            "id": stream_id if not stream_id.startswith("msg_") else f"msg_{len(messages)}",
                            "role": role,
                            "content": content,
                            "timestamp": timestamp.isoformat(),
                            "stream_id": stream_id,
                            "metadata": {
                                "importance": item.get("importance", 0.5),
                                "context_count": 0,
                            }
                        })
        
        # Если L0 пуст, пробуем L1 (сессии)
        if not messages and hasattr(agent.memory, 'redis_store'):
            sessions = await agent.memory.redis_store.l1_get_sessions()
            # L1 содержит сессии, не отдельные сообщения, поэтому пропускаем
        
        # Функция для парсинга stream_id для сортировки
        def parse_stream_id_for_sort(msg):
            stream_id = msg.get("stream_id", "0-0")
            if "-" in stream_id:
                try:
                    ts_part, seq_part = stream_id.split("-", 1)
                    # Парсим timestamp и sequence из stream_id
                    ts = int(ts_part) if ts_part.isdigit() else 0
                    seq = int(seq_part.split("-")[0]) if seq_part.split("-")[0].isdigit() else 0
                    return (ts, seq)
                except:
                    return (0, 0)
            return (0, 0)
        
        # Сортируем по timestamp, затем по stream_id, затем по роли (user перед assistant)
        # stream_id гарантирует порядок в Redis Streams
        messages.sort(key=lambda x: (
            x["timestamp"],  # Основная сортировка по timestamp
            parse_stream_id_for_sort(x),  # Затем по stream_id для стабильности
            (0 if x["role"] == "user" else 1)  # user перед assistant при одинаковом timestamp
        ))
        
        # Ограничиваем количество (после разделения пар может быть больше чем limit)
        # Берем последние N сообщений (самые новые)
        messages = messages[-limit:] if len(messages) > limit else messages
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get chat history: {e}")
        # Возвращаем пустой список вместо ошибки
    
    return messages


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, agent: FractalAgent = Depends(get_agent_from_main)):
    """
    Отправить сообщение агенту.
    
    Args:
        request: Запрос с сообщением и опциональным user_id
        agent: Экземпляр FractalAgent (из dependency injection)
    
    Returns:
        ChatResponse с ответом агента и метаданными
    """
    # Если указан user_id, можно было бы переключить агента, но для простоты используем текущего
    # В будущем можно добавить multi-user поддержку
    response = await agent.chat(request.message)
    
    return ChatResponse(
        response=response.content,
        context_count=len(response.context_used),
        strategies_used=response.strategies_used,
        processing_time_ms=response.processing_time_ms,
    )

