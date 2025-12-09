"""
OpenAI Embeddings wrapper.

Реализует требование IMPROVEMENTS.md п. 2.1
"""

import os
import logging
from typing import Optional
import numpy as np
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """
    Обёртка для OpenAI Embeddings API.
    
    Автоматически используется в FractalMemory если embedding_func не передан.
    """
    
    def __init__(self, model: str = None, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found. Embeddings will fail if called.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Получить вектор для текста.
        
        Args:
            text: Текст для векторизации
            
        Returns:
            numpy array с embedding или None если клиент не инициализирован
        """
        if not self.client:
            logger.warning("OpenAI client not initialized (missing API key)")
            return None
            
        try:
            # Замена переносов строк для улучшения качества
            text = text.replace("\n", " ").strip()
            if not text:
                logger.warning("Empty text provided for embedding")
                return None
                
            response = await self.client.embeddings.create(
                input=[text],
                model=self.model
            )
            
            embedding = response.data[0].embedding
            # Конвертируем в numpy array для совместимости с FractalMemory
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

