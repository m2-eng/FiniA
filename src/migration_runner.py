#!/usr/bin/env python3
#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Database Migration Runner for FiniA
#
"""
Database Migration Runner

Manages incremental database schema migrations using versioned SQL files.
Ensures migrations are applied in order and tracks applied versions.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import List, Tuple, Optional
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger("uvicorn.error")


class MigrationRunner:
    """
    Database migration runner for managing schema versions.
    
    Migrations are stored as SQL files in db/migrations/ with naming convention:
    XXX_description.sql (e.g., 001_initial_schema.sql, 002_add_planning.sql)
    
    The special file 000_schema_migrations_table.sql is always executed first
    to create the migrations tracking table.
    """
    
    def __init__(self, db_config: dict, migrations_dir: Optional[Path] = None, progress_callback: Optional[callable] = None):
        """
        Initialize migration runner.
        
        Args:
            db_config: Dictionary with keys: host, port, user, password, database
            migrations_dir: Optional custom migrations directory path
            progress_callback: Optional callback function called with progress updates
                              Signature: callback(phase, message, current, total)
                              where phase is 'preparing', 'executing', or 'complete'
        """
        self.db_config = db_config
        self.progress_callback = progress_callback
        
        if migrations_dir is None:
            # Default: db/migrations relative to project root
            project_root = Path(__file__).parent.parent
            self.migrations_dir = project_root / "db" / "migrations"
        else:
            self.migrations_dir = Path(migrations_dir)
        
        if not self.migrations_dir.exists():
            raise FileNotFoundError(f"Migrations directory not found: {self.migrations_dir}")
    
    def _get_connection(self) -> pymysql.Connection:
        """Create database connection."""
        return pymysql.connect(
            host=self.db_config.get('host', 'localhost'),
            port=self.db_config.get('port', 3306),
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            charset='utf8mb4',
            cursorclass=DictCursor
        )
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of migration content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_applied_migrations(self, connection: pymysql.Connection) -> List[dict]:
        """
        Get list of already applied migrations from database.
        
        Returns:
            List of dicts with keys: version, description, checksum, applied_at
        """
        with connection.cursor() as cursor:
            if not self._migrations_table_exists(cursor):
                return []

            cursor.execute("""
                SELECT version, description, checksum, applied_at 
                FROM schema_migrations 
                ORDER BY version
            """)
            return cursor.fetchall()

    def _migrations_table_exists(self, cursor: DictCursor) -> bool:
        """Check whether the schema_migrations table exists."""
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_name = 'schema_migrations'
        """, (self.db_config['database'],))
        return cursor.fetchone()['count'] > 0
    
    def _get_migration_files(self) -> List[Tuple[str, Path]]:
        """
        Get sorted list of migration files.
        
        Returns:
            List of tuples (version, file_path) sorted by version
        """
        migrations = []
        
        for file_path in self.migrations_dir.glob("*.sql"):
            filename = file_path.stem
            # Extract version from filename (XXX_description.sql)
            if '_' in filename:
                version = filename.split('_')[0]
                migrations.append((version, file_path))
        
        # Sort by version (string sort works for zero-padded numbers)
        migrations.sort(key=lambda x: x[0])
        return migrations
    
    def _verify_checksum(self, version: str, content: str, stored_checksum: str) -> bool:
        """
        Verify migration file hasn't been modified after being applied.
        
        Args:
            version: Migration version
            content: Current file content
            stored_checksum: Checksum stored in database
            
        Returns:
            True if checksums match
        """
        current_checksum = self._calculate_checksum(content)
        if current_checksum != stored_checksum:
            logger.error(
                f"Migration {version} checksum mismatch! "
                f"File may have been modified after application."
            )
            logger.error(f"  Expected: {stored_checksum}")
            logger.error(f"  Current:  {current_checksum}")
            return False
        return True
    
    def _parse_sql_statements(self, content: str) -> List[str]:
        """
        Parse SQL content into individual statements, respecting DELIMITER directives.
        
        Handles MySQL-specific DELIMITER syntax for triggers, procedures, etc.
        
        Args:
            content: Raw SQL content
            
        Returns:
            List of executable SQL statements
        """
        statements = []
        current_delimiter = ";"
        buffer = ""
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            # Check for DELIMITER directive
            if line.upper().startswith('DELIMITER'):
                parts = line.split(maxsplit=1)
                if len(parts) > 1:
                    current_delimiter = parts[1].strip()
                    logger.debug(f"Changed delimiter to: {current_delimiter}")
                continue
            
            # Skip empty lines and comments
            if not line or line.startswith('--') or line.startswith('#'):
                continue
            
            # Add line to buffer
            if buffer:
                buffer += "\n" + line
            else:
                buffer = line
            
            # Check if statement ends with current delimiter
            if buffer.rstrip().endswith(current_delimiter):
                # Remove the delimiter from the end
                statement = buffer.rstrip()
                if statement.endswith(current_delimiter):
                    statement = statement[:-len(current_delimiter)].rstrip()
                
                if statement:
                    statements.append(statement)
                buffer = ""
        
        # Add any remaining content
        if buffer.strip():
            statements.append(buffer.strip())
        
        return statements
    
    def _extract_object_name(self, statement: str) -> str:
        """
        Extract the name of the database object being created/modified.
        
        Examples:
          'CREATE TABLE `tbl_account`' -> 'tbl_account'
          'ALTER TABLE `tbl_transaction`' -> 'tbl_transaction'
          'CREATE VIEW `vw_year_overview`' -> 'vw_year_overview'
          'CREATE TRIGGER `trg_update_timestamp`' -> 'trg_update_timestamp'
          'CREATE INDEX `idx_user_id`' -> 'idx_user_id'
          'INSERT INTO `tbl_accountType`' -> 'tbl_accountType'
        
        Args:
            statement: SQL statement
            
        Returns:
            Object name or fallback description
        """
        import re
        
        # Pattern to extract table/view/trigger/index name
        patterns = [
            r'(?:CREATE|ALTER)\s+TABLE\s+`?(\w+)`?',
            r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+`?(\w+)`?',
            r'CREATE\s+TRIGGER\s+`?(\w+)`?',
            r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+`?(\w+)`?',
            r'INSERT\s+INTO\s+`?(\w+)`?',
            r'UPDATE\s+`?(\w+)`?',
            r'DELETE\s+FROM\s+`?(\w+)`?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: return first 50 chars of statement
        return statement[:50].strip()
    
    def _execute_migration(
        self, 
        connection: pymysql.Connection, 
        version: str, 
        description: str,
        content: str,
        statement_counter: dict = None
    ) -> int:
        """
        Execute a single migration and record it.
        
        Args:
            connection: Database connection
            version: Migration version
            description: Migration description
            content: SQL content to execute
            statement_counter: Dict with 'current' and 'total' keys for progress tracking
            
        Returns:
            Execution time in milliseconds
        """
        checksum = self._calculate_checksum(content)
        start_time = time.time()
        
        try:
            with connection.cursor() as cursor:
                # Parse SQL statements respecting DELIMITER directives
                statements = self._parse_sql_statements(content)
                
                # Process each statement
                for stmt_idx, statement in enumerate(statements, 1):
                    if statement.strip():
                        logger.debug(f"Executing: {statement[:80]}...")
                        
                        # Extract object name for progress display
                        obj_name = self._extract_object_name(statement)
                        
                        # Execute statement
                        cursor.execute(statement)
                        
                        # Report progress at statement level
                        if self.progress_callback and statement_counter:
                            statement_counter['current'] += 1
                            message = f"✓ {obj_name}"
                            self.progress_callback(
                                'executing', 
                                message, 
                                statement_counter['current'], 
                                statement_counter['total']
                            )
                
                connection.commit()
                
                # Record migration in schema_migrations table
                # Always record, even for version 000 (schema migrations table itself)
                execution_time = int((time.time() - start_time) * 1000)
                cursor.execute("""
                    INSERT INTO schema_migrations 
                    (version, description, checksum, execution_time_ms)
                    VALUES (%s, %s, %s, %s)
                """, (version, description, checksum, execution_time))
                connection.commit()
                return execution_time
                
        except Exception as e:
            connection.rollback()
            logger.error(f"Error executing migration {version}: {e}")
            raise
    
    def _count_total_statements(self, migration_files: List[Tuple[str, Path]], applied_versions: dict) -> int:
        """
        Count total SQL statements across all pending migrations.
        
        Args:
            migration_files: List of migration files
            applied_versions: Dict of already applied migrations
            
        Returns:
            Total count of statements to execute
        """
        total = 0
        for version, file_path in migration_files:
            if version not in applied_versions:  # Only count pending migrations
                content = file_path.read_text(encoding='utf-8')
                statements = self._parse_sql_statements(content)
                total += len([s for s in statements if s.strip()])
        return total
    
    def run_migrations(self, dry_run: bool = False) -> dict:
        """
        Run all pending migrations.
        
        Args:
            dry_run: If True, only show what would be executed without applying
            
        Returns:
            Dictionary with migration results:
            {
                'applied': List of applied migration versions,
                'skipped': List of already applied versions,
                'total_time_ms': Total execution time
            }
        """
        logger.info("Starting database migration check...")
        
        connection = self._get_connection()
        results = {
            'applied': [],
            'skipped': [],
            'total_time_ms': 0
        }
        
        try:
            # Get list of applied migrations
            applied_migrations = self._get_applied_migrations(connection)
            applied_versions = {m['version']: m for m in applied_migrations}
            
            # Get list of migration files
            migration_files = self._get_migration_files()
            
            if not migration_files:
                logger.info("No migration files found")
                if self.progress_callback:
                    self.progress_callback('complete', 'Keine Migrationen erforderlich', 0, 0)
                return results
            
            logger.info(f"Found {len(migration_files)} migration file(s)")
            logger.info(f"Already applied: {len(applied_versions)} migration(s)")
            
            # Count total statements in pending migrations
            total_statements = self._count_total_statements(migration_files, applied_versions)
            
            # Notify callback about total statements
            if self.progress_callback:
                if total_statements > 0:
                    self.progress_callback('preparing', f'Insgesamt {total_statements} Migrationsschritte zu ausführen...', 0, total_statements)
                else:
                    self.progress_callback('complete', 'Alle Migrationen sind aktuell!', 0, 0)
                    return results
            
            # Global counter for tracking statement progress
            statement_counter = {'current': 0, 'total': total_statements}
            
            # Process each migration
            for idx, (version, file_path) in enumerate(migration_files, 1):
                description = file_path.stem.split('_', 1)[1] if '_' in file_path.stem else file_path.stem
                content = file_path.read_text(encoding='utf-8')
                
                if version in applied_versions:
                    # Verify checksum
                    if not self._verify_checksum(version, content, applied_versions[version]['checksum']):
                        raise ValueError(f"Migration {version} integrity check failed!")
                    
                    results['skipped'].append(version)
                    logger.debug(f"Migration {version} already applied, skipping")
                else:
                    # Apply new migration
                    if dry_run:
                        logger.info(f"[DRY RUN] Would apply migration {version}: {description}")
                        results['applied'].append(version)
                    else:
                        if self.progress_callback:
                            self.progress_callback('executing', f'Lädt: {description}...', statement_counter['current'], statement_counter['total'])
                        
                        logger.info(f"Applying migration {version}: {description}")
                        execution_time = self._execute_migration(
                            connection, version, description, content,
                            statement_counter=statement_counter
                        )
                        results['applied'].append(version)
                        results['total_time_ms'] += execution_time
                        logger.info(f"  ✓ Applied in {execution_time}ms")
                        if self.progress_callback:
                            self.progress_callback('executing', f'✓ {description} ({execution_time}ms)', statement_counter['current'], statement_counter['total'])
            
            if results['applied']:
                logger.info(f"Successfully applied {len(results['applied'])} migration(s)")
                if self.progress_callback:
                    self.progress_callback('complete', f'✓ {len(results["applied"])} Migrationen erfolgreich angewendet!', statement_counter['total'], statement_counter['total'])
            else:
                logger.info("All migrations up to date")
                if self.progress_callback:
                    self.progress_callback('complete', 'Alle Migrationen sind aktuell!', statement_counter['current'], statement_counter['total'])
            
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if self.progress_callback:
                self.progress_callback('error', f'Fehler: {str(e)}', 0, 0)
            raise
        finally:
            connection.close()
    
    def get_current_version(self) -> Optional[str]:
        """
        Get the currently applied database version.
        
        Returns:
            Latest migration version or None if no migrations applied
        """
        connection = self._get_connection()
        try:
            applied = self._get_applied_migrations(connection)
            if applied:
                return applied[-1]['version']
            return None
        finally:
            connection.close()

    def get_status(self) -> dict:
        """
        Get migration status without applying changes.

        Returns:
            Dictionary with status details and pending migrations
        """
        connection = self._get_connection()
        try:
            with connection.cursor() as cursor:
                migrations_table_exists = self._migrations_table_exists(cursor)

            applied_migrations = self._get_applied_migrations(connection)
            applied_versions = {m['version']: m for m in applied_migrations}

            migration_files = self._get_migration_files()
            pending = []

            for version, file_path in migration_files:
                description = file_path.stem.split('_', 1)[1] if '_' in file_path.stem else file_path.stem
                content = file_path.read_text(encoding='utf-8')

                if version in applied_versions:
                    if not self._verify_checksum(version, content, applied_versions[version]['checksum']):
                        raise ValueError(f"Migration {version} integrity check failed!")
                    continue

                pending.append({
                    "version": version,
                    "description": description
                })

            current_version = applied_migrations[-1]['version'] if applied_migrations else None

            return {
                "migrations_table_exists": migrations_table_exists,
                "current_version": current_version,
                "pending": pending,
                "pending_count": len(pending),
                "is_initial": len(applied_versions) == 0 and len(pending) > 0,
                "needs_upgrade": len(applied_versions) > 0 and len(pending) > 0
            }
        finally:
            connection.close()
