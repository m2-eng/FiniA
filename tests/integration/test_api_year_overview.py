#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Year Overview API integration tests (Phase 3)
# Issue #32: Implementing a test bench
#
import pytest
import logging
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.api


class TestYearOverviewAPI:
    """Test year overview aggregation endpoints."""
    
    def test_get_account_balances(self, api_client, test_config, account_factory, 
                                  transaction_factory):
        """Test GET /year-overview/account-balances returns account balances."""
        account_id = account_factory.create(startAmount=Decimal('1000.00'))
        transaction_factory.create(account_id, amount=Decimal('500.00'))
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/account-balances",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Account balances retrieved for year {year}")
    
    def test_get_account_balances_monthly(self, api_client, test_config, account_factory,
                                         transaction_factory):
        """Test GET /year-overview/account-balances-monthly returns monthly data."""
        account_id = account_factory.create()
        
        # Create transactions spread over months
        transaction_factory.create_batch(account_id, count=5)
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/account-balances-monthly",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Monthly account balances retrieved")
    
    def test_get_investments(self, api_client, test_config, account_factory):
        """Test GET /year-overview/investments returns investment accounts."""
        # Create investment account (type=2)
        account_factory.create(type=2, name="Investment Account")
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/investments",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Investments overview retrieved")
    
    def test_get_loans(self, api_client, test_config, account_factory):
        """Test GET /year-overview/loans returns loan accounts."""
        # Create loan account (type=3)
        account_factory.create(type=3, name="Loan Account")
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/loans",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Loans overview retrieved")
    
    def test_get_securities(self, api_client, test_config, share_factory):
        """Test GET /year-overview/securities returns securities overview."""
        share_factory.create_batch(count=3)
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/securities",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Securities overview retrieved")
    
    def test_get_assets_month_end(self, api_client, test_config, account_factory,
                                  transaction_factory):
        """Test GET /year-overview/assets-month-end returns end-of-month assets."""
        account_id = account_factory.create(startAmount=Decimal('5000.00'))
        transaction_factory.create_batch(account_id, count=10)
        
        year = datetime.now().year
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/year-overview/assets-month-end",
            params={'year': year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict) or isinstance(data, list)
        logger.info(f"✓ Month-end assets retrieved")


class TestYearsListAPI:
    """Test years list endpoint."""
    
    def test_get_available_years(self, api_client, test_config, account_factory,
                                transaction_factory):
        """Test GET /years/ returns available years."""
        account_id = account_factory.create()
        transaction_factory.create_batch(account_id, count=5)
        
        response = api_client.get(f"{test_config['api_base_url']}/api/years/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list) or 'years' in data
        
        # Should contain current year
        current_year = datetime.now().year
        years = data if isinstance(data, list) else data.get('years', [])
        
        if years:
            assert current_year in years or str(current_year) in [str(y) for y in years]
        
        logger.info(f"✓ Available years retrieved")
