#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Shares API integration tests (Phase 3)
# Issue #32: Implementing a test bench
#
import pytest
import logging
from decimal import Decimal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.api


class TestSharesListAPI:
    """Test shares list endpoints."""
    
    def test_get_shares_list(self, api_client, test_config, share_factory):
        """Test GET /shares/ returns all shares."""
        share_factory.create_batch(count=5)
        
        response = api_client.get(f"{test_config['api_base_url']}/api/shares/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list) or 'shares' in data
        logger.info(f"✓ Shares list returned")


class TestSharesCRUDAPI:
    """Test shares CRUD operations."""
    
    def test_create_share(self, api_client, test_config, db_cursor):
        """Test POST /shares/shares/ creates new share."""
        share_data = {
            'name': 'Test AG',
            'isin': 'DE0001234567',
            'wkn': '123456'
        }
        
        # Temporarily remove Content-Type header to allow multipart/form-data
        original_content_type = api_client.headers.pop('Content-Type', None)
        try:
            response = api_client.post(
                f"{test_config['api_base_url']}/api/shares/",
                data=share_data,
                files={}
            )
        finally:
            if original_content_type:
                api_client.headers['Content-Type'] = original_content_type
        
        if response.status_code not in [200, 201]:
            logger.error(f"Share create failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert 'share_id' in data or 'id' in data
        share_id = data.get('share_id') or data.get('id')
        
        # Verify in database
        db_cursor.execute("SELECT isin FROM tbl_share WHERE id=%s", (share_id,))
        isin = db_cursor.fetchone()[0]
        
        assert isin == 'DE0001234567'
        logger.info(f"✓ Share created with ID {share_id}")
    
    def test_update_share(self, api_client, test_config, share_factory, db_cursor):
        """Test PUT /shares/shares/{id} updates share."""
        share_id = share_factory.create(name="Original Name")
        
        update_data = {
            'name': 'Updated Share Name',
            'isin': 'DE0001234567',
            'wkn': '123456'
        }
        
        # Temporarily remove Content-Type header to allow multipart/form-data
        original_content_type = api_client.headers.pop('Content-Type', None)
        try:
            response = api_client.put(
                f"{test_config['api_base_url']}/api/shares/{share_id}",
                data=update_data,
                files={}
            )
        finally:
            if original_content_type:
                api_client.headers['Content-Type'] = original_content_type
        
        assert response.status_code == 200
        
        # Verify update
        db_cursor.execute("SELECT name FROM tbl_share WHERE id=%s", (share_id,))
        name = db_cursor.fetchone()[0]
        
        assert name == 'Updated Share Name'
        logger.info(f"✓ Share {share_id} updated")
    
    def test_delete_share(self, api_client, test_config, share_factory, db_cursor):
        """Test DELETE /shares/shares/{id} deletes share."""
        share_id = share_factory.create()
        
        response = api_client.delete(
            f"{test_config['api_base_url']}/api/shares/{share_id}"
        )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        db_cursor.execute("SELECT COUNT(*) FROM tbl_share WHERE id=%s", (share_id,))
        count = db_cursor.fetchone()[0]
        
        assert count == 0
        logger.info(f"✓ Share {share_id} deleted")


class TestShareHistoryAPI:
    """Test share price history endpoints."""
    
    def test_get_share_history(self, api_client, test_config, share_factory):
        """Test GET /shares/shares/history returns share price history."""
        share_id = share_factory.create()
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/shares/history",
            params={'share_id': share_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list) or 'history' in data
        logger.info(f"✓ Share history retrieved for share {share_id}")
    
    def test_create_share_history(self, api_client, test_config, share_factory, db_cursor):
        """Test POST /shares/shares/history creates history entry."""
        share_id = share_factory.create(isin='DE0001234567')
        
        # Get share ISIN from database
        db_cursor.execute("SELECT isin FROM tbl_share WHERE id=%s", (share_id,))
        isin = db_cursor.fetchone()[0]
        
        history_data = {
            'isin': isin,
            'amount': 125.50,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Temporarily remove Content-Type header to allow multipart/form-data
        original_content_type = api_client.headers.pop('Content-Type', None)
        try:
            response = api_client.post(
                f"{test_config['api_base_url']}/api/shares/history",
                data=history_data,
                files={}
            )
        finally:
            if original_content_type:
                api_client.headers['Content-Type'] = original_content_type
        
        assert response.status_code in [200, 201]
        logger.info(f"✓ Share history entry created")


class TestShareTransactionsAPI:
    """Test share transactions endpoints."""
    
    def test_get_share_transactions(self, api_client, test_config, share_factory):
        """Test GET /shares/shares/transactions returns transactions."""
        share_id = share_factory.create()
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/shares/transactions",
            params={'share_id': share_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list) or 'transactions' in data
        logger.info(f"✓ Share transactions retrieved")
    
    def test_create_share_transaction(self, api_client, test_config, share_factory):
        """Test POST /shares/shares/transactions creates transaction."""
        share_id = share_factory.create(isin='DE0001234567')
        
        transaction_data = {
            'isin': 'DE0001234567',
            'tradingVolume': 10.5,
            'dateTransaction': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Temporarily remove Content-Type header to allow multipart/form-data
        original_content_type = api_client.headers.pop('Content-Type', None)
        try:
            response = api_client.post(
                f"{test_config['api_base_url']}/api/shares/transactions",
                data=transaction_data,
                files={}
            )
        finally:
            if original_content_type:
                api_client.headers['Content-Type'] = original_content_type
        
        assert response.status_code in [200, 201]
        logger.info(f"✓ Share transaction created")
