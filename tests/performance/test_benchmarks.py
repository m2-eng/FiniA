#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Performance benchmark tests (Phase 5)
# Issue #32: Implementing a test bench
#
import pytest
import logging
import time
from decimal import Decimal

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.performance


class TestQueryPerformance:
    """Test database query performance."""
    
    def test_account_list_performance(self, api_client, test_config, account_factory, benchmark):
        """Benchmark account list query performance."""
        # Setup: Create 50 accounts
        account_factory.create_batch(count=50)
        
        def fetch_accounts():
            response = api_client.get(f"{test_config['api_base_url']}/api/accounts/list")
            return response
        
        # Benchmark the query
        result = benchmark(fetch_accounts)
        
        assert result.status_code == 200
        logger.info(f"✓ Account list query benchmark completed")
    
    def test_category_hierarchy_performance(self, api_client, test_config, 
                                           category_factory, benchmark):
        """Benchmark category hierarchy traversal."""
        # Setup: Create 3-level hierarchy with 30 categories
        parent_id = category_factory.create(name="Root")
        
        for i in range(10):
            child_id = category_factory.create(name=f"Level2-{i}", category=parent_id)
            for j in range(2):
                category_factory.create(name=f"Level3-{i}-{j}", category=child_id)
        
        def fetch_hierarchy():
            response = api_client.get(
                f"{test_config['api_base_url']}/api/categories/hierarchy/all"
            )
            return response
        
        result = benchmark(fetch_hierarchy)
        
        assert result.status_code == 200
        logger.info(f"✓ Category hierarchy query benchmark completed")
    
    def test_transaction_list_pagination_performance(self, api_client, test_config,
                                                    account_factory, transaction_factory,
                                                    benchmark):
        """Benchmark transaction list with pagination."""
        # Setup: Create 100 transactions
        account_id = account_factory.create()
        transaction_factory.create_batch(account_id, count=100)
        
        def fetch_transactions():
            response = api_client.get(
                f"{test_config['api_base_url']}/api/transactions/",
                params={'page': 1, 'page_size': 50}
            )
            return response
        
        result = benchmark(fetch_transactions)
        
        assert result.status_code == 200
        logger.info(f"✓ Transaction pagination query benchmark completed")


class TestAPIResponseTimes:
    """Test API endpoint response times."""
    
    def test_year_overview_response_time(self, api_client, test_config, 
                                        account_factory, transaction_factory,
                                        performance_timer):
        """Test year overview API response time (Issue #66 performance fix)."""
        # Setup: Create realistic data
        account_ids = account_factory.create_batch(count=5)
        
        for account_id in account_ids:
            transaction_factory.create_batch(account_id, count=50)
        
        from datetime import datetime
        year = datetime.now().year
        
        with performance_timer as timer:
            response = api_client.get(
                f"{test_config['api_base_url']}/api/year-overview/account-balances",
                params={'year': year}
            )
        
        assert response.status_code == 200
        elapsed_ms = timer.elapsed_ms
        
        # Critical timeout: 2000ms (from .env.test)
        assert elapsed_ms < 2000, f"Year overview took {elapsed_ms}ms (> 2000ms critical timeout)"
        
        logger.info(f"✓ Year overview response time: {elapsed_ms:.2f}ms")
    
    def test_account_income_response_time(self, api_client, test_config,
                                         account_factory, transaction_factory,
                                         performance_timer):
        """Test account income API response time."""
        account_id = account_factory.create(name="Income Performance Test")
        transaction_factory.create_batch(account_id, count=100)
        
        from datetime import datetime
        year = datetime.now().year
        
        with performance_timer as timer:
            response = api_client.get(
                f"{test_config['api_base_url']}/api/accounts/income",
                params={'year': year, 'account': 'Income Performance Test'}
            )
        
        assert response.status_code == 200
        elapsed_ms = timer.elapsed_ms
        
        # Should be fast (< 1000ms)
        assert elapsed_ms < 1000
        
        logger.info(f"✓ Account income response time: {elapsed_ms:.2f}ms")
    
    def test_planning_entries_generation_time(self, api_client, test_config,
                                              account_factory, category_factory,
                                              planning_factory, performance_timer):
        """Test planning entries generation performance."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id, cycle=5)
        
        with performance_timer as timer:
            response = api_client.post(
                f"{test_config['api_base_url']}/api/planning/{planning_id}/entries/generate"
            )
        
        assert response.status_code in [200, 201]
        elapsed_ms = timer.elapsed_ms
        
        # Should be reasonably fast (< 700ms, allowing for DB overhead)
        assert elapsed_ms < 700
        
        logger.info(f"✓ Planning entries generation time: {elapsed_ms:.2f}ms")


class TestBulkOperations:
    """Test bulk operation performance."""
    
    def test_bulk_account_creation(self, account_factory, benchmark):
        """Benchmark bulk account creation."""
        
        def create_10_accounts():
            return account_factory.create_batch(count=10)
        
        result = benchmark(create_10_accounts)
        
        assert len(result) == 10
        logger.info(f"✓ Bulk account creation benchmark completed")
    
    def test_bulk_transaction_creation(self, account_factory, transaction_factory, benchmark):
        """Benchmark bulk transaction creation."""
        account_id = account_factory.create()
        
        def create_50_transactions():
            return transaction_factory.create_batch(account_id, count=50)
        
        result = benchmark(create_50_transactions)
        
        assert len(result) == 50
        logger.info(f"✓ Bulk transaction creation benchmark completed")
    
    def test_bulk_category_creation(self, category_factory, benchmark):
        """Benchmark bulk category creation."""
        
        def create_20_categories():
            return category_factory.create_batch(count=20)
        
        result = benchmark(create_20_categories)
        
        assert len(result) == 20
        logger.info(f"✓ Bulk category creation benchmark completed")


class TestDatabaseOperationPerformance:
    """Test database-specific operation performance."""
    
    def test_database_connection_time(self, db_connection, performance_timer):
        """Test database connection establishment time."""
        
        with performance_timer as timer:
            cursor = db_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        
        elapsed_ms = timer.elapsed_ms
        
        # Should be very fast (< 50ms)
        assert elapsed_ms < 50
        
        logger.info(f"✓ Database connection time: {elapsed_ms:.2f}ms")
    
    def test_complex_join_query_performance(self, db_cursor, account_factory,
                                           category_factory, transaction_factory,
                                           performance_timer):
        """Test complex JOIN query performance."""
        # Setup: Create data
        account_id = account_factory.create()
        category_id = category_factory.create()
        transaction_factory.create_batch(account_id, count=50)
        
        query = """
            SELECT 
                t.id, t.description, t.amount, t.dateValue,
                a.name as account_name,
                c.name as category_name
            FROM tbl_transaction t
            LEFT JOIN tbl_account a ON t.account = a.id
            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t.id
            LEFT JOIN tbl_category c ON ae.category = c.id
            WHERE t.account = %s
            ORDER BY t.dateValue DESC
            LIMIT 100
        """
        
        with performance_timer as timer:
            db_cursor.execute(query, (account_id,))
            results = db_cursor.fetchall()
        
        elapsed_ms = timer.elapsed_ms
        
        # Should be reasonably fast (< 100ms)
        assert elapsed_ms < 100
        
        logger.info(f"✓ Complex JOIN query time: {elapsed_ms:.2f}ms ({len(results)} rows)")
    
    def test_aggregation_query_performance(self, db_cursor, account_factory,
                                          transaction_factory, performance_timer):
        """Test aggregation query performance."""
        account_id = account_factory.create()
        transaction_factory.create_batch(account_id, count=100)
        
        query = """
            SELECT 
                YEAR(dateValue) as year,
                MONTH(dateValue) as month,
                COUNT(*) as count,
                SUM(amount) as total
            FROM tbl_transaction
            WHERE account = %s
            GROUP BY YEAR(dateValue), MONTH(dateValue)
            ORDER BY year DESC, month DESC
        """
        
        with performance_timer as timer:
            db_cursor.execute(query, (account_id,))
            results = db_cursor.fetchall()
        
        elapsed_ms = timer.elapsed_ms
        
        # Should be fast (< 50ms)
        assert elapsed_ms < 50
        
        logger.info(f"✓ Aggregation query time: {elapsed_ms:.2f}ms")


class TestRegressionDetection:
    """Test for performance regression detection."""
    
    def test_year_overview_regression(self, api_client, test_config,
                                     account_factory, transaction_factory):
        """Test year overview doesn't regress (Issue #66 fix validation)."""
        # This is the key performance fix from Issue #66
        # Setup: Create significant data load
        account_ids = account_factory.create_batch(count=10)
        
        for account_id in account_ids:
            transaction_factory.create_batch(account_id, count=100)
        
        from datetime import datetime
        year = datetime.now().year
        
        execution_times = []
        
        # Run 5 times to get average
        for _ in range(5):
            start = time.time()
            response = api_client.get(
                f"{test_config['api_base_url']}/api/year-overview/account-balances",
                params={'year': year}
            )
            end = time.time()
            
            assert response.status_code == 200
            execution_times.append((end - start) * 1000)
        
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # Critical: Must be under 2000ms
        assert avg_time < 2000, f"Average time {avg_time:.2f}ms exceeds 2000ms"
        assert max_time < 2500, f"Max time {max_time:.2f}ms exceeds 2500ms"
        
        logger.info(f"✓ Year overview regression test passed")
        logger.info(f"  Average: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
    
    @pytest.mark.slow
    def test_baseline_comparison(self, api_client, test_config, test_data_bundle):
        """Compare current performance against baseline."""
        # Create standard test dataset
        data = test_data_bundle.create_full_test_scenario(
            num_accounts=5,
            categories_per_account=10
        )
        
        from datetime import datetime
        year = datetime.now().year
        
        # Measure multiple endpoints
        endpoints = [
            f"/api/accounts/list",
            f"/api/categories/hierarchy/all",
            f"/api/year-overview/account-balances?year={year}",
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = api_client.get(f"{test_config['api_base_url']}{endpoint}")
            elapsed = (time.time() - start) * 1000
            
            # All should be under 1000ms
            assert elapsed < 1000, f"{endpoint} took {elapsed:.2f}ms (> 1000ms)"
            
            logger.info(f"✓ {endpoint}: {elapsed:.2f}ms")
