#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Category API integration tests (Phase 3)
# Issue #32: Implementing a test bench
#
import pytest
import logging

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.api


class TestCategoryListAPI:
    """Test category list endpoints."""
    
    def test_get_categories_paginated(self, api_client, test_config, category_factory):
        """Test GET /categories/ returns paginated categories."""
        # Create test categories
        category_factory.create_batch(count=15)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/",
            params={'page': 1, 'page_size': 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'categories' in data
        assert 'page' in data
        assert 'page_size' in data
        assert 'total' in data
        
        assert data['page'] == 1
        assert data['page_size'] == 10
        assert len(data['categories']) <= 10
        
        logger.info(f"✓ Paginated categories returned (total: {data['total']})")
    
    def test_get_categories_hierarchy(self, api_client, test_config, category_factory):
        """Test GET /categories/hierarchy returns hierarchy."""
        # Create parent-child hierarchy
        parent_id = category_factory.create(name="Parent Category")
        category_factory.create(name="Child Category 1", category=parent_id)
        category_factory.create(name="Child Category 2", category=parent_id)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/hierarchy",
            params={'page': 1, 'page_size': 100}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'categories' in data
        categories = data['categories']
        
        # Verify hierarchy structure
        children = [c for c in categories if c.get('parent_id') == parent_id]
        assert len(children) >= 2
        
        logger.info(f"✓ Category hierarchy returned")
    
    def test_get_all_categories_hierarchy(self, api_client, test_config, category_factory):
        """Test GET /categories/hierarchy/all returns all categories."""
        category_factory.create_batch(count=5)
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/hierarchy/all"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'categories' in data
        assert len(data['categories']) >= 5
        
        logger.info(f"✓ All categories hierarchy returned ({len(data['categories'])} categories)")
    
    def test_get_categories_simple_list(self, api_client, test_config, category_factory):
        """Test GET /categories/list returns simple list."""
        category_factory.create_batch(count=3)
        
        response = api_client.get(f"{test_config['api_base_url']}/api/categories/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'categories' in data
        categories = data['categories']
        
        # Verify simple structure (id, name/fullname)
        if categories:
            category = categories[0]
            assert 'id' in category
            
        logger.info(f"✓ Simple categories list returned")


class TestCategoryDetailsAPI:
    """Test individual category CRUD operations."""
    
    def test_get_category_by_id(self, api_client, test_config, category_factory):
        """Test GET /categories/{id} returns category details."""
        category_id = category_factory.create(name="Test Category Details")
        
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/{category_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['id'] == category_id
        assert data['name'] == "Test Category Details"
        
        logger.info(f"✓ Category {category_id} details retrieved")
    
    def test_get_nonexistent_category(self, api_client, test_config):
        """Test GET /categories/{id} with invalid ID returns 404."""
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/999999"
        )
        
        assert response.status_code == 404
        logger.info(f"✓ Non-existent category returns 404")
    
    def test_create_category(self, api_client, test_config, db_cursor):
        """Test POST /categories/ creates new category."""
        category_data = {
            'name': 'New Test Category',
            'parent_id': None
        }
        
        response = api_client.post(
            f"{test_config['api_base_url']}/api/categories/",
            json=category_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert 'id' in data
        category_id = data['id']
        
        # Verify in database
        db_cursor.execute("SELECT name FROM tbl_category WHERE id=%s", (category_id,))
        result = db_cursor.fetchone()
        
        assert result is not None
        assert result[0] == 'New Test Category'
        
        logger.info(f"✓ Category created with ID {category_id}")
    
    def test_update_category(self, api_client, test_config, category_factory, db_cursor):
        """Test PUT /categories/{id} updates category."""
        category_id = category_factory.create(name="Original Category Name")
        
        update_data = {
            'name': 'Updated Category Name'
        }
        
        response = api_client.put(
            f"{test_config['api_base_url']}/api/categories/{category_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        
        # Verify update
        db_cursor.execute("SELECT name FROM tbl_category WHERE id=%s", (category_id,))
        name = db_cursor.fetchone()[0]
        
        assert name == 'Updated Category Name'
        logger.info(f"✓ Category {category_id} updated")
    
    def test_delete_category(self, api_client, test_config, category_factory, db_cursor):
        """Test DELETE /categories/{id} deletes category."""
        category_id = category_factory.create(name="Category to Delete")
        
        response = api_client.delete(
            f"{test_config['api_base_url']}/api/categories/{category_id}"
        )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        db_cursor.execute("SELECT COUNT(*) FROM tbl_category WHERE id=%s", (category_id,))
        count = db_cursor.fetchone()[0]
        
        assert count == 0
        logger.info(f"✓ Category {category_id} deleted")


class TestCategoryHierarchyLogic:
    """Test category hierarchy business logic."""
    
    def test_create_child_category(self, api_client, test_config, category_factory):
        """Test creating child category with parent reference."""
        parent_id = category_factory.create(name="Parent Category")
        
        child_data = {
            'name': 'Child Category',
            'parent_id': parent_id
        }
        
        response = api_client.post(
            f"{test_config['api_base_url']}/api/categories/",
            json=child_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert data.get('parent_id') == parent_id
        logger.info(f"✓ Child category created under parent {parent_id}")
    
    def test_multi_level_hierarchy(self, api_client, test_config, category_factory):
        """Test multi-level category hierarchy."""
        # Create 3-level hierarchy
        level1_id = category_factory.create(name="Level 1")
        level2_id = category_factory.create(name="Level 2", category=level1_id)
        level3_id = category_factory.create(name="Level 3", category=level2_id)
        
        # Fetch hierarchy
        response = api_client.get(
            f"{test_config['api_base_url']}/api/categories/hierarchy/all"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        categories = data['categories']
        
        # Verify all levels exist
        level_ids = [c['id'] for c in categories]
        assert level1_id in level_ids
        assert level2_id in level_ids
        assert level3_id in level_ids
        
        logger.info(f"✓ Multi-level hierarchy validated")
