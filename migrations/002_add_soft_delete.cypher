// Migration 002: Add Soft Delete Fields
// Версия: 2
// Дата: 2025-01-25
// Описание: Добавление полей для soft delete

// ═══════════════════════════════════════════════════════════
// ДОБАВИТЬ ПОЛЯ SOFT DELETE
// ═══════════════════════════════════════════════════════════

// Добавить deleted=false ко всем Entity
MATCH (e:Entity)
WHERE e.deleted IS NULL
SET e.deleted = false;

// Добавить deleted=false ко всем Episode
MATCH (ep:Episode)
WHERE ep.deleted IS NULL
SET ep.deleted = false;

// Добавить deleted=false ко всем Strategy
MATCH (s:Strategy)
WHERE s.deleted IS NULL
SET s.deleted = false;

// Добавить deleted=false ко всем Experience
MATCH (exp:Experience)
WHERE exp.deleted IS NULL
SET exp.deleted = false;

// ═══════════════════════════════════════════════════════════
// INDEXES ДЛЯ SOFT DELETE
// ═══════════════════════════════════════════════════════════

CREATE INDEX entity_deleted_idx IF NOT EXISTS
FOR (e:Entity) ON (e.deleted);

CREATE INDEX episode_deleted_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.deleted);

CREATE INDEX strategy_deleted_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.deleted);

// Composite index для GC (deleted + deleted_at)
CREATE INDEX entity_deleted_at_idx IF NOT EXISTS
FOR (e:Entity) ON (e.deleted, e.deleted_at);

CREATE INDEX episode_deleted_at_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.deleted, ep.deleted_at);

// ═══════════════════════════════════════════════════════════
// MIGRATION RECORD
// ═══════════════════════════════════════════════════════════

MERGE (m:Migration {version: 2})
SET m.applied_at = datetime(),
    m.name = 'add_soft_delete';
