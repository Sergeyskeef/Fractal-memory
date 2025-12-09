// Migration 001: Initial Schema
// Версия: 1
// Дата: 2025-01-25
// Описание: Базовая схема графа и constraints

// ═══════════════════════════════════════════════════════════
// CONSTRAINTS (уникальность ID)
// ═══════════════════════════════════════════════════════════

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
FOR (ep:Episode) REQUIRE ep.id IS UNIQUE;

CREATE CONSTRAINT strategy_id_unique IF NOT EXISTS
FOR (s:Strategy) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT experience_id_unique IF NOT EXISTS
FOR (exp:Experience) REQUIRE exp.id IS UNIQUE;

// ═══════════════════════════════════════════════════════════
// INDEXES (производительность)
// ═══════════════════════════════════════════════════════════

// Entity indexes
CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type);

// Episode indexes
CREATE INDEX episode_timestamp_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.timestamp);

CREATE INDEX episode_source_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.source);

CREATE INDEX episode_level_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.level);

// Strategy indexes
CREATE INDEX strategy_task_type_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.task_types);

// Experience indexes
CREATE INDEX experience_outcome_idx IF NOT EXISTS
FOR (exp:Experience) ON (exp.outcome);

CREATE INDEX experience_task_type_idx IF NOT EXISTS
FOR (exp:Experience) ON (exp.task_type);

// ═══════════════════════════════════════════════════════════
// VECTOR INDEX (semantic search)
// ⚠️ Измени dimensions если используешь другую модель!
// ═══════════════════════════════════════════════════════════

CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};

// ═══════════════════════════════════════════════════════════
// ЗАПИСЬ МИГРАЦИИ
// ═══════════════════════════════════════════════════════════

MERGE (m:Migration {version: 1})
SET m.applied_at = datetime(),
    m.name = 'initial_schema',
    m.description = 'Base schema with constraints and indexes';
