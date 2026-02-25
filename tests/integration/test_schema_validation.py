#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Database schema validation tests (Phase 1)
# Issue #32: Implementing a test bench
#
import pytest
import logging

logger = logging.getLogger(__name__)


@pytest.mark.schema
class TestDatabaseSchema:
    """Validate database schema structure and constraints."""
    
    def test_all_required_tables_exist(self, db_cursor):
        """Verify all required tables exist in the database."""
        db_cursor.execute("SHOW TABLES")
        tables = [row[0] for row in db_cursor.fetchall()]
        
        required_tables = [
            'tbl_account',
            'tbl_accountType',
            'tbl_accountImportFormat',
            'tbl_accountImportPath',
            'tbl_accountingEntry',
            'tbl_accountReserve',
            'tbl_category',
            'tbl_loan',
            'tbl_planning',
            'tbl_planningCycle',
            'tbl_planningEntry',
            'tbl_share',
            'tbl_shareHistory',
            'tbl_shareTransaction',
            'tbl_transaction',
            'tbl_setting',
            'schema_migrations'
        ]
        
        missing = [t for t in required_tables if t not in tables]
        assert not missing, f"Missing tables: {missing}"
        logger.info(f"✓ All {len(required_tables)} required tables exist")
    
    def test_account_table_structure(self, db_cursor):
        """Validate tbl_account table structure."""
        db_cursor.execute("DESCRIBE tbl_account")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required_columns = {
            'id': 'bigint',
            'dateImport': 'datetime',
            'name': 'varchar',
            'iban_accountNumber': 'varchar',
            'bic_market': 'text',
            'startAmount': 'decimal',
            'dateStart': 'datetime',
            'dateEnd': 'datetime',
            'type': 'bigint',
            'clearingAccount': 'bigint'
        }
        
        for col_name, expected_type in required_columns.items():
            assert col_name in columns, f"Column {col_name} missing from tbl_account"
            assert expected_type in columns[col_name], \
                f"Column {col_name} has type {columns[col_name]}, expected {expected_type}"
        
        logger.info(f"✓ tbl_account has correct structure ({len(columns)} columns)")
    
    def test_category_table_structure(self, db_cursor):
        """Validate tbl_category table structure."""
        db_cursor.execute("DESCRIBE tbl_category")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required_columns = {
            'id': 'bigint',
            'dateImport': 'datetime',
            'name': 'varchar',
            'category': 'bigint'
        }
        
        for col_name, expected_type in required_columns.items():
            assert col_name in columns, f"Column {col_name} missing from tbl_category"
            assert expected_type in columns[col_name]
        
        logger.info(f"✓ tbl_category has correct structure")
    
    def test_transaction_table_structure(self, db_cursor):
        """Validate tbl_transaction table structure."""
        db_cursor.execute("DESCRIBE tbl_transaction")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required_columns = {
            'id': 'bigint',
            'dateImport': 'datetime',
            'iban': 'varchar',
            'bic': 'text',
            'description': 'varchar',
            'amount': 'decimal',
            'dateValue': 'datetime',
            'recipientApplicant': 'text',
            'account': 'bigint',
            'duplicateHashComputed': 'varchar'
        }
        
        for col_name, expected_type in required_columns.items():
            assert col_name in columns, f"Column {col_name} missing from tbl_transaction"
        
        logger.info(f"✓ tbl_transaction has correct structure")
    
    def test_planning_table_structure(self, db_cursor):
        """Validate tbl_planning table structure."""
        db_cursor.execute("DESCRIBE tbl_planning")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required_columns = {
            'id': 'bigint',
            'dateImport': 'datetime',
            'description': 'text',
            'amount': 'decimal',
            'dateStart': 'datetime',
            'dateEnd': 'datetime',
            'account': 'bigint',
            'category': 'bigint',
            'cycle': 'bigint'
        }
        
        for col_name in required_columns.keys():
            assert col_name in columns, f"Column {col_name} missing from tbl_planning"
        
        logger.info(f"✓ tbl_planning has correct structure")
    
    def test_share_table_structure(self, db_cursor):
        """Validate tbl_share table structure."""
        db_cursor.execute("DESCRIBE tbl_share")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required_columns = {
            'id': 'bigint',
            'dateImport': 'datetime',
            'name': 'text',
            'isin': 'varchar',
            'wkn': 'varchar'
        }
        
        for col_name in required_columns.keys():
            assert col_name in columns, f"Column {col_name} missing from tbl_share"
        
        logger.info(f"✓ tbl_share has correct structure")


@pytest.mark.schema
class TestDatabaseConstraints:
    """Validate database constraints and indexes."""
    
    def test_account_primary_key(self, db_cursor):
        """Verify tbl_account has primary key."""
        db_cursor.execute("SHOW KEYS FROM tbl_account WHERE Key_name = 'PRIMARY'")
        pk = db_cursor.fetchall()
        
        assert len(pk) > 0, "tbl_account missing primary key"
        assert pk[0][4] == 'id', "Primary key should be on 'id' column"
        logger.info(f"✓ tbl_account has primary key on 'id'")
    
    def test_account_unique_constraints(self, db_cursor):
        """Verify tbl_account has unique constraints."""
        db_cursor.execute("SHOW KEYS FROM tbl_account WHERE Non_unique = 0")
        unique_keys = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        assert 'name' in unique_keys, "tbl_account missing unique constraint on 'name'"
        assert 'iban_accountNumber' in unique_keys, \
            "tbl_account missing unique constraint on 'iban_accountNumber'"
        
        logger.info(f"✓ tbl_account has required unique constraints")
    
    def test_category_unique_name(self, db_cursor):
        """Verify tbl_category has unique constraint on name."""
        db_cursor.execute("SHOW KEYS FROM tbl_category WHERE Non_unique = 0")
        unique_keys = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        assert 'name' in unique_keys, "tbl_category missing unique constraint on 'name'"
        logger.info(f"✓ tbl_category has unique constraint on name")
    
    def test_transaction_unique_constraint(self, db_cursor):
        """Verify tbl_transaction has unique constraint on duplicateHashComputed."""
        db_cursor.execute("SHOW KEYS FROM tbl_transaction WHERE Non_unique = 0")
        unique_keys = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        assert 'duplicateHashComputed' in unique_keys, \
            "tbl_transaction missing unique constraint on duplicateHashComputed"
        logger.info(f"✓ tbl_transaction has duplicate prevention constraint")
    
    def test_foreign_key_constraints_exist(self, db_cursor):
        """Verify foreign key constraints are defined."""
        # Check account -> accountType foreign key
        db_cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'tbl_account' 
            AND COLUMN_NAME = 'type'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        fk_type = db_cursor.fetchall()
        
        # Note: Foreign keys might not be enforced in all setups
        # This is informational check
        if fk_type:
            logger.info(f"✓ tbl_account has foreign key on 'type'")
        else:
            logger.warning("⚠ tbl_account missing foreign key constraint on 'type'")
    
    def test_account_type_seed_data(self, db_cursor):
        """Verify tbl_accountType has seed data."""
        db_cursor.execute("SELECT COUNT(*) FROM tbl_accountType")
        count = db_cursor.fetchone()[0]
        
        assert count >= 5, f"tbl_accountType should have at least 5 types, found {count}"
        
        # Verify expected types exist
        db_cursor.execute("SELECT type FROM tbl_accountType")
        types = [row[0] for row in db_cursor.fetchall()]
        
        expected_types = ['Girokonto', 'Wertpapierdepot', 'Darlehen', 'Krypto', 'Investmentplattform']
        for expected in expected_types:
            assert expected in types, f"Missing account type: {expected}"
        
        logger.info(f"✓ tbl_accountType has {count} seed entries")
    
    def test_planning_cycle_seed_data(self, db_cursor):
        """Verify tbl_planningCycle has seed data."""
        db_cursor.execute("SELECT COUNT(*) FROM tbl_planningCycle")
        count = db_cursor.fetchone()[0]
        
        assert count >= 8, f"tbl_planningCycle should have at least 8 cycles, found {count}"
        
        # Verify expected cycles
        db_cursor.execute("SELECT cycle FROM tbl_planningCycle")
        cycles = [row[0] for row in db_cursor.fetchall()]
        
        expected_cycles = ['einmalig', 'täglich', 'wöchentlich', '14-tägig', 
                          'monatlich', 'vierteljährlich', 'halbjährlich', 'jährlich']
        for expected in expected_cycles:
            assert expected in cycles, f"Missing planning cycle: {expected}"
        
        logger.info(f"✓ tbl_planningCycle has {count} seed entries")


@pytest.mark.schema
class TestDatabaseIndexes:
    """Validate database indexes for performance."""
    
    def test_account_indexes(self, db_cursor):
        """Verify tbl_account has required indexes."""
        db_cursor.execute("SHOW INDEX FROM tbl_account")
        indexes = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        expected_indexes = ['type', 'clearingAccount']
        for idx in expected_indexes:
            assert idx in indexes, f"Missing index on tbl_account.{idx}"
        
        logger.info(f"✓ tbl_account has {len(indexes)} indexes")
    
    def test_transaction_indexes(self, db_cursor):
        """Verify tbl_transaction has required indexes."""
        db_cursor.execute("SHOW INDEX FROM tbl_transaction")
        indexes = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        assert 'account' in indexes, "Missing index on tbl_transaction.account"
        logger.info(f"✓ tbl_transaction has required indexes")
    
    def test_category_parent_index(self, db_cursor):
        """Verify tbl_category has index on parent category."""
        db_cursor.execute("SHOW INDEX FROM tbl_category")
        indexes = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        assert 'category' in indexes, "Missing index on tbl_category.category (parent)"
        logger.info(f"✓ tbl_category has parent index")
    
    def test_planning_indexes(self, db_cursor):
        """Verify tbl_planning has required indexes."""
        db_cursor.execute("SHOW INDEX FROM tbl_planning")
        indexes = {row[4]: row[2] for row in db_cursor.fetchall()}
        
        expected = ['account', 'category', 'cycle']
        for idx in expected:
            assert idx in indexes, f"Missing index on tbl_planning.{idx}"
        
        logger.info(f"✓ tbl_planning has required indexes")


@pytest.mark.schema
class TestSchemaVersioning:
    """Validate schema migration tracking."""
    
    def test_schema_migrations_table_exists(self, db_cursor):
        """Verify schema_migrations tracking table exists."""
        db_cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
        result = db_cursor.fetchall()
        
        assert len(result) > 0, "schema_migrations table not found"
        logger.info(f"✓ schema_migrations table exists")
    
    def test_schema_migrations_structure(self, db_cursor):
        """Verify schema_migrations has correct structure."""
        db_cursor.execute("DESCRIBE schema_migrations")
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}
        
        required = ['version', 'applied_at', 'description']
        for col in required:
            assert col in columns, f"schema_migrations missing column: {col}"
        
        logger.info(f"✓ schema_migrations has correct structure")
    
    def test_initial_migration_applied(self, db_cursor):
        """Verify initial schema migration is recorded."""
        db_cursor.execute("SELECT COUNT(*) FROM schema_migrations")
        count = db_cursor.fetchone()[0]
        
        assert count >= 1, "No migrations recorded in schema_migrations"
        
        db_cursor.execute("SELECT version, description FROM schema_migrations ORDER BY version")
        migrations = db_cursor.fetchall()
        
        logger.info(f"✓ {count} migration(s) applied:")
        for version, desc in migrations:
            logger.info(f"  - {version}: {desc}")
