#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Planning API integration tests (Phase 3)
# Issue #32: Implementing a test bench
#
import pytest
import logging
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.api


class TestPlanningCyclesAPI:
    """Test planning cycles endpoints."""
    
    def test_get_planning_cycles(self, api_client, test_config):
        """Test GET /planning/cycles returns all planning cycles."""
        response = api_client.get(f"{test_config['api_base_url']}/api/planning/cycles")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 8  # Seed data has 8 cycles
        
        # Verify expected cycles
        cycle_names = [c['cycle'] for c in data]
        expected = ['einmalig', 'täglich', 'wöchentlich', '14-tägig', 
                   'monatlich', 'vierteljährlich', 'halbjährlich', 'jährlich']
        
        for expected_cycle in expected:
            assert expected_cycle in cycle_names
        
        logger.info(f"✓ Planning cycles returned ({len(data)} cycles)")


class TestPlanningListAPI:
    """Test planning list endpoints."""
    
    def test_get_planning_list(self, api_client, test_config, account_factory, 
                               category_factory, planning_factory):
        """Test GET /planning/ returns paginated planning entries."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        
        # Create planning entries
        planning_factory.create_batch(account_id, [category_id], count=5)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/planning/",
            params={'page': 1, 'page_size': 100}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'plannings' in data
        assert data['total'] >= 5
        logger.info(f"✓ Planning list returned")


class TestPlanningCRUDAPI:
    """Test planning CRUD operations."""
    
    def test_get_planning_by_id(self, api_client, test_config, account_factory,
                                category_factory, planning_factory):
        """Test GET /planning/{id} returns planning details."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/planning/{planning_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['id'] == planning_id
        assert data['account_id'] == account_id
        assert data['category_id'] == category_id
        
        logger.info(f"✓ Planning {planning_id} details retrieved")
    
    def test_create_planning(self, api_client, test_config, account_factory,
                            category_factory, db_cursor):
        """Test POST /planning/ creates new planning."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        
        planning_data = {
            'description': 'Test Planning Entry',
            'amount': 500.00,
            'dateStart': datetime.now().isoformat(),
            'dateEnd': None,
            'account_id': account_id,
            'category_id': category_id,
            'cycle_id': 5  # Monthly
        }
        
        response = api_client.post(
            f"{test_config['api_base_url']}/api/planning/",
            json=planning_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert 'id' in data
        planning_id = data['id']
        
        # Verify in database
        db_cursor.execute("SELECT amount FROM tbl_planning WHERE id=%s", (planning_id,))
        amount = db_cursor.fetchone()[0]
        
        assert abs(float(amount) - 500.00) < 0.01
        logger.info(f"✓ Planning created with ID {planning_id}")
    
    def test_update_planning(self, api_client, test_config, account_factory,
                            category_factory, planning_factory, db_cursor):
        """Test PUT /planning/{id} updates planning."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id, amount=Decimal('200.00'))
        
        # Fetch current planning data to get all required fields
        fetch_response = api_client.get(
            f"{test_config['api_base_url']}/api/planning/{planning_id}"
        )
        current_data = fetch_response.json()
        
        update_data = {
            'amount': 750.00,
            'description': 'Updated Planning',
            'dateStart': current_data['dateStart'],
            'dateEnd': current_data.get('dateEnd'),
            'account_id': current_data['account_id'],
            'category_id': current_data['category_id'],
            'cycle_id': current_data['cycle_id']
        }
        
        response = api_client.put(
            f"{test_config['api_base_url']}/api/planning/{planning_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        
        # Verify update
        db_cursor.execute("SELECT amount FROM tbl_planning WHERE id=%s", (planning_id,))
        amount = db_cursor.fetchone()[0]
        
        assert abs(float(amount) - 750.00) < 0.01
        logger.info(f"✓ Planning {planning_id} updated")
    
    def test_delete_planning(self, api_client, test_config, account_factory,
                            category_factory, planning_factory, db_cursor):
        """Test DELETE /planning/{id} deletes planning."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id)
        
        response = api_client.delete(
            f"{test_config['api_base_url']}/api/planning/{planning_id}"
        )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        db_cursor.execute("SELECT COUNT(*) FROM tbl_planning WHERE id=%s", (planning_id,))
        count = db_cursor.fetchone()[0]
        
        assert count == 0
        logger.info(f"✓ Planning {planning_id} deleted")


class TestPlanningEntriesAPI:
    """Test planning entries generation and management."""
    
    def test_get_planning_entries(self, api_client, test_config, account_factory,
                                  category_factory, planning_factory):
        """Test GET /planning/{id}/entries returns planning entries."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/planning/{planning_id}/entries"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'entries' in data or isinstance(data, list)
        logger.info(f"✓ Planning entries retrieved for planning {planning_id}")
    
    def test_generate_planning_entries(self, api_client, test_config, account_factory,
                                      category_factory, planning_factory):
        """Test POST /planning/{id}/entries/generate creates future entries."""
        account_id = account_factory.create()
        category_id = category_factory.create()
        planning_id = planning_factory.create(account_id, category_id, cycle=5)
        
        response = api_client.post(
            f"{test_config['api_base_url']}/api/planning/{planning_id}/entries/generate"
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        # Should have generated entries
        if 'entries' in data:
            assert len(data['entries']) > 0
        
        logger.info(f"✓ Planning entries generated for planning {planning_id}")
