#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Account API integration tests (Phase 3)
# Issue #32: Implementing a test bench
#
import pytest
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.api


class TestAccountListAPI:
    """Test account list endpoints."""
    
    def test_get_account_list(self, api_client, test_config, account_factory):
        """Test GET /accounts/list returns all accounts."""
        # Create test accounts
        account_factory.create_batch(count=3)
        
        response = api_client.get(f"{test_config['api_base_url']}/api/accounts/list")
        
        assert response.status_code == 200
        data = response.json()
        
        # API returns paginated response
        assert isinstance(data, dict)
        assert 'accounts' in data
        assert 'total' in data
        
        accounts = data['accounts']
        assert isinstance(accounts, list)
        assert len(accounts) >= 3
        assert data['total'] >= 3
        
        # Verify structure of first account
        if accounts:
            account = accounts[0]
            required_fields = ['id', 'name', 'iban_accountNumber', 'type']
            for field in required_fields:
                assert field in account, f"Missing field: {field}"
        
        logger.info(f"✓ Account list returned {len(accounts)} accounts (total: {data['total']})")
    
    def test_get_girokonto_list(self, api_client, test_config, account_factory):
        """Test GET /accounts/girokonto/list returns only Girokonten names (for Grafana)."""
        # Create mixed account types
        account_factory.create(name="Girokonto 1", type=1)
        account_factory.create(name="Depot 1", type=2)  # Wertpapierdepot
        account_factory.create(name="Girokonto 2", type=1)
        
        response = api_client.get(f"{test_config['api_base_url']}/api/accounts/girokonto/list")
        
        assert response.status_code == 200
        data = response.json()
        
        # API returns simple list response (for Grafana queries)
        assert isinstance(data, dict)
        assert 'accounts' in data
        
        accounts = data['accounts']
        assert isinstance(accounts, list)
        # This endpoint returns only account names (strings), not full objects
        assert len(accounts) == 2, f"Expected 2 Girokonten, got {len(accounts)}"
        for account in accounts:
            assert isinstance(account, str), f"Expected string (account name), got {type(account)}"
        
        logger.info(f"✓ Girokonto list returned {len(accounts)} account names")


class TestAccountDetailsAPI:
    """Test individual account CRUD operations."""
    
    def test_get_account_by_id(self, api_client, test_config, account_factory):
        """Test GET /accounts/{account_id} returns account details."""
        account_id = account_factory.create(name="Test Account Details")
        
        response = api_client.get(f"{test_config['api_base_url']}/api/accounts/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['id'] == account_id
        assert data['name'] == "Test Account Details"
        assert 'iban_accountNumber' in data
        assert 'startAmount' in data
        
        logger.info(f"✓ Account {account_id} details retrieved")
    
    def test_get_nonexistent_account(self, api_client, test_config):
        """Test GET /accounts/{account_id} with invalid ID returns 404."""
        nonexistent_id = 999999
        
        response = api_client.get(f"{test_config['api_base_url']}/api/accounts/{nonexistent_id}")
        
        assert response.status_code == 404
        logger.info(f"✓ Non-existent account returns 404")
    
    def test_update_account(self, api_client, test_config, account_factory, db_cursor):
        """Test PUT /accounts/{account_id} updates account."""
        account_id = account_factory.create(name="Original Name")
        
        # Get existing account data first
        get_response = api_client.get(f"{test_config['api_base_url']}/api/accounts/{account_id}")
        assert get_response.status_code == 200
        account_data = get_response.json()
        
        # Remove 'id' field as it's not part of AccountData model
        account_data.pop('id', None)
        
        # Fix clearingAccount: GET may return name (string) but PUT expects ID (int)
        if isinstance(account_data.get('clearingAccount'), str):
            account_data['clearingAccount'] = None
        
        # Update only the desired fields
        account_data['name'] = 'Updated Account Name'
        account_data['startAmount'] = 5000.0
        
        # Send complete account data to API
        response = api_client.put(
            f"{test_config['api_base_url']}/api/accounts/{account_id}",
            json=account_data
        )
        
        assert response.status_code == 200
        
        # Verify update in database
        db_cursor.execute("SELECT name, startAmount FROM tbl_account WHERE id=%s", (account_id,))
        name, amount = db_cursor.fetchone()
        
        assert name == "Updated Account Name"
        assert abs(float(amount) - 5000.0) < 0.01
        
        logger.info(f"✓ Account {account_id} updated successfully")
    
    def test_delete_account(self, api_client, test_config, account_factory, db_cursor):
        """Test DELETE /accounts/{account_id} deletes account."""
        account_id = account_factory.create(name="Account to Delete")
        
        response = api_client.delete(f"{test_config['api_base_url']}/api/accounts/{account_id}")
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        db_cursor.execute("SELECT COUNT(*) FROM tbl_account WHERE id=%s", (account_id,))
        count = db_cursor.fetchone()[0]
        
        assert count == 0, "Account should be deleted"
        logger.info(f"✓ Account {account_id} deleted successfully")


class TestAccountTypesAPI:
    """Test account types endpoints."""
    
    def test_get_account_types_list(self, api_client, test_config):
        """Test GET /accounts/types/list returns all account types."""
        response = api_client.get(f"{test_config['api_base_url']}/api/accounts/types/list")
        
        assert response.status_code == 200
        data = response.json()
        
        #API returns dict with 'types' key
        assert isinstance(data, dict)
        assert 'types' in data
        
        types = data['types']
        assert isinstance(types, list)
        assert len(types) >= 5  # Seed data has 5 types
        
        # Verify expected types exist
        type_names = [t['type'] for t in types]
        expected_types = ['Girokonto', 'Wertpapierdepot', 'Darlehen', 'Krypto', 'Investment-Plattform']
        
        for expected in expected_types:
            assert expected in type_names, f"Missing account type: {expected}"
        
        logger.info(f"✓ Account types list returned {len(types)} types")


class TestAccountIncomeExpensesAPI:
    """Test account income/expense breakdown endpoints."""
    
    def test_get_account_income(self, api_client, test_config, account_factory, 
                                category_factory, transaction_factory):
        """Test GET /accounts/income returns income breakdown."""
        account_id = account_factory.create(name="Income Test Account")
        category_id = category_factory.create(name="Salary")
        
        # Create income transactions (positive amounts)
        transaction_factory.create(account_id, amount=Decimal('3000.00'))
        transaction_factory.create(account_id, amount=Decimal('500.00'))
        
        from datetime import datetime
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/income",
            params={'year': year, 'account': 'Income Test Account'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should contain income breakdown
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Account income retrieved for year {year}")
    
    def test_get_account_expenses(self, api_client, test_config, account_factory, 
                                  category_factory, transaction_factory):
        """Test GET /accounts/expenses returns expense breakdown."""
        account_id = account_factory.create(name="Expense Test Account")
        category_id = category_factory.create(name="Groceries")
        
        # Create expense transactions (negative amounts)
        transaction_factory.create(account_id, amount=Decimal('-150.00'))
        transaction_factory.create(account_id, amount=Decimal('-200.00'))
        
        from datetime import datetime
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/expenses",
            params={'year': year, 'account': 'Expense Test Account'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Account expenses retrieved for year {year}")
    
    def test_get_account_summary(self, api_client, test_config, account_factory, 
                                transaction_factory):
        """Test GET /accounts/summary returns monthly summary."""
        account_id = account_factory.create(name="Summary Test Account")
        
        # Create mixed transactions
        transaction_factory.create(account_id, amount=Decimal('1000.00'))
        transaction_factory.create(account_id, amount=Decimal('-500.00'))
        
        from datetime import datetime
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/summary",
            params={'year': year, 'account': 'Summary Test Account'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Summary should contain Haben (positive), Soll (negative), Gesamt (net)
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Account summary retrieved for year {year}")


class TestAccountAggregateAPI:
    """Test aggregate account endpoints (all-giro, all-loans, all-accounts)."""
    
    def test_get_all_giro_income(self, api_client, test_config, account_factory, 
                                 transaction_factory):
        """Test GET /accounts/all-giro/income aggregates all Girokonten."""
        # Create Girokonten (type=1)
        acc1 = account_factory.create(type=1, name="Giro 1")
        acc2 = account_factory.create(type=1, name="Giro 2")
        
        transaction_factory.create(acc1, amount=Decimal('1000.00'))
        transaction_factory.create(acc2, amount=Decimal('2000.00'))
        
        from datetime import datetime
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/all-giro/income",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ All-Giro income aggregated for year {year}")
    
    def test_get_all_accounts_summary(self, api_client, test_config, account_factory, 
                                     transaction_factory):
        """Test GET /accounts/all-accounts/summary aggregates all accounts."""
        # Create different account types
        acc1 = account_factory.create(type=1)
        acc2 = account_factory.create(type=2)
        acc3 = account_factory.create(type=3)
        
        transaction_factory.create(acc1, amount=Decimal('500.00'))
        transaction_factory.create(acc2, amount=Decimal('-200.00'))
        transaction_factory.create(acc3, amount=Decimal('1000.00'))
        
        from datetime import datetime
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/all-accounts/summary",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ All-accounts summary aggregated for year {year}")


class TestAccountImportAPI:
    """Test account import endpoints."""
    
    @pytest.mark.skip(reason="Requires file upload - implement when needed")
    def test_import_accounts_yaml(self, api_client, test_config):
        """Test POST /accounts/import-yaml imports accounts from YAML."""
        # Requires multipart file upload
        yaml_content = """
        account_data:
          - name: "Imported Account 1"
            iban_accountNumber: "DE89370400440532013000"
            bic_market: "COBADEFFXXX"
            startAmount: 1000.0
            type: 1
        """
        
        # TODO: Implement file upload test
        pass
