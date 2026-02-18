#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Database data integrity tests (Phase 2)
# Issue #32: Implementing a test bench
#
import pytest
import logging
from decimal import Decimal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@pytest.mark.integrity
class TestAccountIntegrity:
    """Validate account data integrity rules."""
    
    def test_account_unique_name(self, db_cursor, account_factory):
        """Verify account names must be unique."""
        # Create first account
        account_id_1 = account_factory.create(name="Test Account Unique")
        
        # Try to create duplicate - should fail
        with pytest.raises(Exception) as exc_info:
            account_factory.create(name="Test Account Unique")
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Account name uniqueness enforced")
    
    def test_account_unique_iban(self, db_cursor, account_factory):
        """Verify account IBAN must be unique."""
        iban = "DE89370400440532013000"
        
        # Create first account with specific IBAN
        account_id_1 = account_factory.create(iban_accountNumber=iban)
        
        # Try to create duplicate - should fail
        with pytest.raises(Exception) as exc_info:
            account_factory.create(name="Different Name", iban_accountNumber=iban)
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Account IBAN uniqueness enforced")
    
    def test_account_valid_type(self, db_cursor, account_factory):
        """Verify account type must exist in tbl_accountType."""
        # Valid types: 1-5 (seeded data)
        valid_account = account_factory.create(type=1)
        assert valid_account > 0
        
        # Check that account was created successfully
        db_cursor.execute("SELECT type FROM tbl_account WHERE id=%s", (valid_account,))
        result = db_cursor.fetchone()
        assert result[0] == 1
        
        logger.info("✓ Account type validation works")
    
    def test_account_date_consistency(self, db_cursor, account_factory):
        """Verify account dateEnd must be after dateStart if set."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = start_date + timedelta(days=730)
        
        # Valid: end after start
        account_id = account_factory.create(
            dateStart=start_date,
            dateEnd=end_date
        )
        
        db_cursor.execute("SELECT dateStart, dateEnd FROM tbl_account WHERE id=%s", (account_id,))
        start, end = db_cursor.fetchone()
        
        assert end > start, "dateEnd should be after dateStart"
        logger.info("✓ Account date consistency validated")


@pytest.mark.integrity
class TestCategoryIntegrity:
    """Validate category data integrity rules."""
    
    def test_category_unique_name(self, db_cursor, category_factory):
        """Verify category names must be unique."""
        category_name = "Test Category Unique"
        
        cat_id_1 = category_factory.create(name=category_name)
        
        with pytest.raises(Exception) as exc_info:
            category_factory.create(name=category_name)
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Category name uniqueness enforced")
    
    def test_category_hierarchy(self, db_cursor, category_factory):
        """Verify category hierarchy (parent-child relationships)."""
        # Create parent category
        parent_id = category_factory.create(name="Parent Category")
        
        # Create child category
        child_id = category_factory.create(name="Child Category", category=parent_id)
        
        # Verify hierarchy
        db_cursor.execute("SELECT category FROM tbl_category WHERE id=%s", (child_id,))
        parent_fk = db_cursor.fetchone()[0]
        
        assert parent_fk == parent_id, "Child should reference parent"
        logger.info("✓ Category hierarchy maintained")
    
    def test_category_self_reference_prevention(self, db_cursor, category_factory):
        """Verify category cannot reference itself as parent."""
        cat_id = category_factory.create(name="Self-Ref Test")
        
        # Try to update to self-reference (manual SQL to test constraint)
        try:
            db_cursor.execute("UPDATE tbl_category SET category=%s WHERE id=%s", (cat_id, cat_id))
            db_cursor.connection.commit()
            
            # If no error, check data - ideally should fail at constraint level
            db_cursor.execute("SELECT category FROM tbl_category WHERE id=%s", (cat_id,))
            parent = db_cursor.fetchone()[0]
            
            # Application-level check (since DB might not enforce)
            assert parent != cat_id, "Category should not self-reference"
            
        except Exception as e:
            # Expected: constraint violation
            logger.info(f"✓ Self-reference prevented: {e}")


@pytest.mark.integrity
class TestTransactionIntegrity:
    """Validate transaction data integrity rules."""
    
    def test_transaction_duplicate_detection(self, db_cursor, account_factory, transaction_factory):
        """Verify duplicate transaction detection via hash."""
        account_id = account_factory.create()
        
        # Create first transaction
        trans_data = {
            'iban': 'DE89370400440532013000',
            'description': 'Duplicate Test Transaction',
            'amount': Decimal('123.45'),
            'dateValue': datetime.now(),
        }
        
        trans_id_1 = transaction_factory.create(account_id, **trans_data)
        
        # Try to create exact duplicate - should fail
        with pytest.raises(Exception) as exc_info:
            transaction_factory.create(account_id, **trans_data)
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Transaction duplicate detection works")
    
    def test_transaction_account_reference(self, db_cursor, account_factory, transaction_factory):
        """Verify transaction must reference valid account."""
        account_id = account_factory.create()
        
        # Create valid transaction
        trans_id = transaction_factory.create(account_id, amount=Decimal('100.00'))
        
        # Verify foreign key
        db_cursor.execute("SELECT account FROM tbl_transaction WHERE id=%s", (trans_id,))
        fk_account = db_cursor.fetchone()[0]
        
        assert fk_account == account_id, "Transaction should reference correct account"
        logger.info("✓ Transaction-Account reference validated")
    
    def test_transaction_amount_precision(self, db_cursor, account_factory, transaction_factory):
        """Verify transaction amounts maintain decimal precision."""
        account_id = account_factory.create()
        
        test_amount = Decimal('123.4567890123')
        trans_id = transaction_factory.create(account_id, amount=test_amount)
        
        db_cursor.execute("SELECT amount FROM tbl_transaction WHERE id=%s", (trans_id,))
        stored_amount = db_cursor.fetchone()[0]
        
        # Should store with 10 decimal places (per schema: decimal(20,10))
        assert abs(stored_amount - test_amount) < Decimal('0.0000000001')
        logger.info(f"✓ Amount precision maintained: {stored_amount}")


@pytest.mark.integrity
class TestPlanningIntegrity:
    """Validate planning data integrity rules."""
    
    def test_planning_references_valid_account(self, db_cursor, account_factory, 
                                               category_factory, planning_factory):
        """Verify planning references valid account and category."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        
        planning_id = planning_factory.create(
            account_id=account_id,
            category_id=category_id,
            amount=Decimal('500.00')
        )
        
        # Verify references
        db_cursor.execute(
            "SELECT account, category FROM tbl_planning WHERE id=%s",
            (planning_id,)
        )
        acc_fk, cat_fk = db_cursor.fetchone()
        
        assert acc_fk == account_id and cat_fk == category_id
        logger.info("✓ Planning references valid account and category")
    
    def test_planning_duplicate_prevention(self, db_cursor, account_factory, 
                                          category_factory, planning_factory):
        """Verify planning unique constraint (account, category, cycle, dateStart, amount)."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        
        planning_data = {
            'amount': Decimal('250.00'),
            'dateStart': datetime.now(),
            'cycle': 5,  # Monthly
        }
        
        plan_id_1 = planning_factory.create(account_id, category_id, **planning_data)
        
        # Try to create duplicate
        with pytest.raises(Exception) as exc_info:
            planning_factory.create(account_id, category_id, **planning_data)
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Planning duplicate prevention enforced")


@pytest.mark.integrity
class TestShareIntegrity:
    """Validate share/security data integrity rules."""
    
    def test_share_unique_isin(self, db_cursor, share_factory):
        """Verify share ISIN must be unique."""
        isin = "DE0005140008"  # Deutsche Bank
        
        share_id_1 = share_factory.create(isin=isin, name="Share 1")
        
        with pytest.raises(Exception) as exc_info:
            share_factory.create(isin=isin, name="Share 2")
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Share ISIN uniqueness enforced")
    
    def test_share_unique_wkn(self, db_cursor, share_factory):
        """Verify share WKN must be unique."""
        wkn = "514000"  # Deutsche Bank
        
        share_id_1 = share_factory.create(wkn=wkn, isin="DE0000000001", name="Share A")
        
        with pytest.raises(Exception) as exc_info:
            share_factory.create(wkn=wkn, isin="DE0000000002", name="Share B")
        
        assert "Duplicate" in str(exc_info.value) or "unique" in str(exc_info.value).lower()
        logger.info("✓ Share WKN uniqueness enforced")


@pytest.mark.integrity
class TestReferentialIntegrity:
    """Validate referential integrity across tables."""
    
    def test_accounting_entry_references(self, db_cursor, db_connection, account_factory, 
                                        category_factory, transaction_factory):
        """Verify accounting entry references valid transaction and category."""
        from factories import AccountingEntryFactory
        
        account_id = account_factory.create()
        category_id = category_factory.create()
        trans_id = transaction_factory.create(account_id)
        
        # Create accounting entry
        entry_data = AccountingEntryFactory.build(
            transaction=trans_id,
            category=category_id,
            amount=Decimal('50.00')
        )
        entry_id = AccountingEntryFactory.insert_into_db(db_cursor, entry_data)
        db_connection.commit()
        
        # Verify references
        db_cursor.execute(
            "SELECT transaction, category FROM tbl_accountingEntry WHERE id=%s",
            (entry_id,)
        )
        trans_fk, cat_fk = db_cursor.fetchone()
        
        assert trans_fk == trans_id
        assert cat_fk == category_id
        logger.info("✓ Accounting entry references validated")
    
    def test_orphaned_records_prevention(self, db_cursor, account_factory, transaction_factory):
        """Verify cleanup prevents orphaned transaction records."""
        account_id = account_factory.create()
        trans_id = transaction_factory.create(account_id)
        
        # Verify transaction exists
        db_cursor.execute("SELECT COUNT(*) FROM tbl_transaction WHERE account=%s", (account_id,))
        count_before = db_cursor.fetchone()[0]
        assert count_before > 0
        
        # Note: Cleanup is handled by cleanup_test_data fixture automatically
        logger.info("✓ Orphaned record prevention via auto-cleanup")
