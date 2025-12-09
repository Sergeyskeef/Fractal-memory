// ═══════════════════════════════════════════════════════════
// ⚠️ КРИТИЧНО: Создать ДО добавления данных!
// Без индексов система деградирует через 2-4 недели
// ═══════════════════════════════════════════════════════════

// 1. Entity name (самый частый запрос)
CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

// 2. Episode timestamp (temporal queries)
CREATE INDEX episode_timestamp_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.timestamp);

// 3. Vector index для semantic search
// ⚠️ Измени dimensions если используешь другую модель!
CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};

// 4. Composite: importance + time
CREATE INDEX entity_importance_time_idx IF NOT EXISTS
FOR (e:Entity) ON (e.importance_score, e.last_accessed);

// 5. Strategy success rate
CREATE INDEX strategy_success_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.success_rate);

// 6. Soft delete index (для GC)
CREATE INDEX entity_deleted_idx IF NOT EXISTS
FOR (e:Entity) ON (e.deleted, e.deleted_at);

CREATE INDEX episode_deleted_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.deleted, ep.deleted_at);

// 7. Memory level
CREATE INDEX memory_level_idx IF NOT EXISTS
FOR (m:Memory) ON (m.level);

// Проверка
SHOW INDEXES;

