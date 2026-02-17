-- ========================================
-- Schema Migrations Management Table
-- Version: Initial
-- Purpose: Track applied database migrations
-- ========================================

CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `version` VARCHAR(50) NOT NULL PRIMARY KEY COMMENT 'Migration version identifier (e.g., 001, 002, 003)',
  `description` VARCHAR(255) NOT NULL COMMENT 'Human-readable description of the migration',
  `checksum` VARCHAR(64) NOT NULL COMMENT 'SHA-256 hash of migration file for integrity verification',
  `applied_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp when migration was applied',
  `execution_time_ms` INT UNSIGNED DEFAULT NULL COMMENT 'Duration of migration execution in milliseconds'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='Database schema version tracking';

-- Index for faster version lookups (only create if not exists)
CREATE INDEX IF NOT EXISTS idx_applied_at ON `schema_migrations` (`applied_at`);
