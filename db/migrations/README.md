# Database Migrations

This directory contains all database migrations for FiniA.

## Overview

The migration system manages schema changes and ensures that:
- All changes are traceable
- Migrations run in the correct order
- Duplicate or corrupted migrations are detected (checksum validation)
- The current database state is auditable

## Migration Files

Each migration is a SQL file with the following naming scheme:

```
XXX_description.sql
```

Where:
- `XXX` is a 3-digit version number (000, 001, 002, ...)
- `description` is a short, descriptive name (lowercase, underscores)

### Examples:
- `000_schema_migrations_table.sql` - Tracking table for migrations
- `001_initial_schema.sql` - Initial database schema
- `002_add_user_preferences.sql` - New table for user settings
- `003_alter_transaction_index.sql` - Index optimization

## How Migrations Run

1. **Automatically on startup**: The `MigrationRunner` executes on application start
2. **Order**: Migrations run in ascending version order
3. **Idempotency**: Already applied migrations are skipped
4. **Checksums**: Changes to applied migrations are detected and cause a failure

## Creating a Migration

### 1. Create a new migration file

```bash
# Determine the next version number (e.g., 002)
# Create the file

```

### 2. Define the SQL schema

```sql
-- ========================================
-- Migration: Short description
-- Version: 002
-- ========================================

-- Your SQL statements here
CREATE TABLE IF NOT EXISTS `tbl_new_table` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- More statements...
```

### 3. Start the application

The migration runs automatically on the next start:

```bash
python src/main.py
```

### 4. Check the logs

```
INFO: Running database migrations...
INFO: Applied 1 migration(s) successfully
INFO:   ✓ 002: description (145ms)
```

## Tracking Table

All applied migrations are stored in the `schema_migrations` table:

```sql
SELECT * FROM schema_migrations ORDER BY applied_at DESC;
```

Columns:
- `version` - Version number (e.g., "001")
- `description` - Description from the filename
- `checksum` - SHA-256 hash of the SQL contents
- `applied_at` - Time the migration was applied
- `execution_time_ms` - Execution duration in milliseconds

## Best Practices

### ✅ Recommended

- **Small, focused migrations**: One change per migration
- **Descriptive names**: `add_user_avatar_column` instead of `change1`
- **Comments**: Explain complex SQL changes
- **IF NOT EXISTS**: For safer CREATE statements
- **Backups before major changes**: Especially for data migrations

### ❌ Avoid

- **Editing applied migrations**: Never modify a migration that has been run
- **Skipping version numbers**: No gaps in numbering
- **Multiple unrelated changes**: Keep migrations focused
- **No rollback plan**: Document rollback steps for critical changes

## Migration Runner (Python)

The `MigrationRunner` lives in `src/migration_runner.py`.

### Key Methods

```python
runner = MigrationRunner(db_config, migrations_dir)

# Run migrations
result = runner.run_migrations(dry_run=False)

# Get current version
current_version = runner.get_current_version()

# Dry-run (preview without changes)
result = runner.run_migrations(dry_run=True)
```

### Return Structure of `run_migrations()`

```python
{
    'status': 'success' | 'error',
    'current_version': '001',
    'pending_count': 2,
    'applied_count': 2,
    'applied': [
        {
            'version': '001',
            'description': 'initial_schema',
            'execution_time_ms': 145
        }
    ],
    'skipped': [],
    'error': None  # or exception message
}
```

## Error Handling

### Migration failed

**Symptom**: The application does not start, error in the log:
```
ERROR: Database migration failed: Checksum mismatch for migration 001
```

**Cause**: An applied migration was modified

**Fix**:
1. Check which migration is affected: `SELECT * FROM schema_migrations WHERE version = '001'`
2. **Option A - Rollback**: Restore the original file
3. **Option B - Force**: Delete the entry from `schema_migrations` (dev only!)
   ```sql
   DELETE FROM schema_migrations WHERE version = '001';
   ```
4. Restart the application

### Migration stuck

**Symptom**: The application hangs on startup

**Cause**: Long-running migration (e.g., large data migration)

**Fix**:
- Wait or check MariaDB logs
- For very long migrations: run separately with higher timeouts

## Maintenance

### Old migration cleanup (optional)

After several releases, you can consolidate old migrations into a baseline:

1. Create a new squashed migration (e.g., `050_baseline_v2.sql`)
2. Include all schema changes up to that point
3. Document which migrations are replaced
4. Archive old migrations (do not delete!)

## Integration

The migration system is integrated at startup in [src/api/main.py](../../src/api/main.py):

```python
from migration_runner import MigrationRunner

migrations_dir = Path(__file__).parent.parent.parent / "db" / "migrations"
migration_runner = MigrationRunner(db_config, str(migrations_dir))
result = migration_runner.run_migrations(dry_run=False)
```

## More Information

- [Database Schema Documentation](../../docs/database/schema.md)
- [Production Deployment Guide](../../docs/deployment/production.md)
- [Backup Strategy](../../docs/backup.md)
