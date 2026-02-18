#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Extended assertion helpers and utilities for API/Database testing
#
import json
import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import requests


logger = logging.getLogger(__name__)


class APIAssertions:
    """Advanced API response assertion methods."""
    
    @staticmethod
    def assert_response_success(response: requests.Response, 
                               expected_code: int = 200,
                               message: str = "") -> Dict[str, Any]:
        """Assert successful API response and return JSON data."""
        assert response.status_code == expected_code, \
            f"{message}\nExpected {expected_code}, got {response.status_code}:\n{response.text}"
        
        try:
            data = response.json()
            return data
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON response: {e}\nBody: {response.text}")
    
    @staticmethod
    def assert_contains_fields(response_data: Dict[str, Any], 
                              required_fields: List[str],
                              path: str = "") -> None:
        """Assert response contains all required fields at given JSON path."""
        missing = [f for f in required_fields if f not in response_data]
        assert not missing, f"Missing fields in {path}: {missing}\nGot: {list(response_data.keys())}"
    
    @staticmethod
    def assert_field_type(response_data: Dict[str, Any],
                         field_name: str,
                         expected_type: type,
                         message: str = "") -> None:
        """Assert field contains expected data type."""
        if field_name not in response_data:
            raise AssertionError(f"Field not found: {field_name}")
        
        actual_type = type(response_data[field_name])
        assert actual_type == expected_type, \
            f"Field '{field_name}' has type {actual_type.__name__}, expected {expected_type.__name__}. {message}"
    
    @staticmethod
    def assert_field_value(response_data: Dict[str, Any],
                          field_name: str,
                          expected_value: Any,
                          message: str = "") -> None:
        """Assert field has expected value."""
        assert field_name in response_data, f"Field not found: {field_name}"
        actual = response_data[field_name]
        assert actual == expected_value, \
            f"Field '{field_name}': expected {expected_value}, got {actual}. {message}"
    
    @staticmethod
    def assert_field_in_range(response_data: Dict[str, Any],
                             field_name: str,
                             min_value: Any = None,
                             max_value: Any = None,
                             message: str = "") -> None:
        """Assert numeric field is in range."""
        assert field_name in response_data, f"Field not found: {field_name}"
        value = response_data[field_name]
        
        if min_value is not None:
            assert value >= min_value, \
                f"Field '{field_name}' ({value}) < minimum ({min_value}). {message}"
        
        if max_value is not None:
            assert value <= max_value, \
                f"Field '{field_name}' ({value}) > maximum ({max_value}). {message}"
    
    @staticmethod
    def assert_response_pagination(response_data: Dict[str, Any],
                                  expected_page: int,
                                  expected_page_size: int,
                                  expected_total: Optional[int] = None) -> None:
        """Assert pagination fields are correct."""
        assert response_data.get('page') == expected_page, \
            f"Page mismatch: expected {expected_page}, got {response_data.get('page')}"
        
        assert response_data.get('page_size') == expected_page_size, \
            f"Page size mismatch: expected {expected_page_size}, got {response_data.get('page_size')}"
        
        if expected_total is not None:
            assert response_data.get('total') == expected_total, \
                f"Total mismatch: expected {expected_total}, got {response_data.get('total')}"


class DatabaseAssertions:
    """Advanced database assertion methods."""
    
    @staticmethod
    def assert_record_exists(cursor,
                            table: str,
                            expected_values: Dict[str, Any],
                            message: str = "") -> Dict[str, Any]:
        """Assert record exists with specified values and return the record."""
        where_clause = ' AND '.join([f"`{k}`=%s" for k in expected_values.keys()])
        query = f"SELECT * FROM {table} WHERE {where_clause}"
        
        try:
            cursor.execute(query, tuple(expected_values.values()))
            record = cursor.fetchone()
            
            assert record is not None, \
                f"No record found in {table} with {expected_values}. {message}"
            
            # Convert to dict
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, record))
        
        except Exception as e:
            raise AssertionError(f"Error querying {table}: {e}. {message}")
    
    @staticmethod
    def assert_record_count(cursor,
                           table: str,
                           expected_count: int,
                           where_clause: str = "",
                           params: tuple = (),
                           message: str = "") -> None:
        """Assert table has expected number of records."""
        query = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        
        assert count == expected_count, \
            f"Expected {expected_count} records in {table}, got {count}. {message}"
    
    @staticmethod
    def assert_field_values(cursor,
                           table: str,
                           where_clause: str,
                           params: tuple,
                           expected_values: Dict[str, Any],
                           message: str = "") -> None:
        """Assert all records matching criteria have expected values."""
        select_clause = ','.join(expected_values.keys())
        query = f"SELECT {select_clause} FROM {table} WHERE {where_clause}"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        assert len(records) > 0, f"No records found matching criteria. {message}"
        
        columns = [col[0] for col in cursor.description]
        for record in records:
            record_dict = dict(zip(columns, record))
            for field, expected in expected_values.items():
                actual = record_dict.get(field)
                assert actual == expected, \
                    f"Field '{field}': expected {expected}, got {actual}. {message}"
    
    @staticmethod
    def assert_foreign_key_exists(cursor,
                                 parent_table: str,
                                 parent_id: int,
                                 parent_key: str = 'id',
                                 child_table: str = None,
                                 child_fk_column: str = None,
                                 message: str = "") -> None:
        """Assert referenced foreign key exists."""
        query = f"SELECT COUNT(*) FROM {parent_table} WHERE `{parent_key}`=%s"
        cursor.execute(query, (parent_id,))
        
        exists = cursor.fetchone()[0] > 0
        assert exists, f"Foreign key {parent_id} not found in {parent_table}.{parent_key}. {message}"
    
    @staticmethod
    def assert_unique_constraint(cursor,
                                table: str,
                                fields: Dict[str, Any],
                                exclude_id: Optional[int] = None,
                                message: str = "") -> None:
        """Assert unique constraint would be violated if inserting duplicate."""
        where_clause = ' AND '.join([f"`{k}`=%s" for k in fields.keys()])
        if exclude_id:
            where_clause += " AND `id`!=%s"
        
        query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        params = tuple(fields.values())
        if exclude_id:
            params += (exclude_id,)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        
        assert count == 0, \
            f"Unique constraint violated: duplicate found in {table} with {fields}. {message}"
    
    @staticmethod
    def assert_data_integrity(cursor,
                             parent_table: str,
                             child_table: str,
                             fk_column: str,
                             message: str = "") -> None:
        """Assert all foreign keys in child table reference valid parent records."""
        query = f"""
            SELECT COUNT(*) FROM {child_table} c
            WHERE NOT EXISTS (
                SELECT 1 FROM {parent_table} p 
                WHERE p.id = c.{fk_column}
            ) AND c.{fk_column} IS NOT NULL
        """
        
        cursor.execute(query)
        invalid_count = cursor.fetchone()[0]
        
        assert invalid_count == 0, \
            f"Data integrity violation: {invalid_count} orphaned records in {child_table}. {message}"


class DecimalAssertions:
    """Assertions for Decimal/Money fields."""
    
    @staticmethod
    def assert_decimal_equals(actual: Decimal,
                             expected: Decimal,
                             precision: int = 2,
                             message: str = "") -> None:
        """Assert decimal values match within precision."""
        actual_rounded = actual.quantize(Decimal(10) ** -precision)
        expected_rounded = expected.quantize(Decimal(10) ** -precision)
        
        assert actual_rounded == expected_rounded, \
            f"Expected {expected_rounded}, got {actual_rounded}. {message}"
    
    @staticmethod
    def assert_decimal_in_range(value: Decimal,
                               min_val: Decimal = None,
                               max_val: Decimal = None,
                               message: str = "") -> None:
        """Assert decimal is within range."""
        if min_val is not None:
            assert value >= min_val, \
                f"Value {value} < minimum {min_val}. {message}"
        
        if max_val is not None:
            assert value <= max_val, \
                f"Value {value} > maximum {max_val}. {message}"
    
    @staticmethod
    def assert_decimal_sum(values: List[Decimal],
                          expected_sum: Decimal,
                          message: str = "") -> None:
        """Assert list of decimals sums to expected value."""
        actual_sum = sum(values, Decimal('0'))
        assert actual_sum == expected_sum, \
            f"Sum mismatch: expected {expected_sum}, got {actual_sum}. {message}"


class DateTimeAssertions:
    """Assertions for DateTime fields."""
    
    @staticmethod
    def assert_datetime_recent(dt: datetime,
                              seconds_ago: int = 60,
                              message: str = "") -> None:
        """Assert datetime is within recent time window."""
        from datetime import datetime as dt_class, timedelta
        
        recent_cutoff = dt_class.now() - timedelta(seconds=seconds_ago)
        assert dt >= recent_cutoff, \
            f"Datetime {dt} is older than {seconds_ago} seconds. {message}"
    
    @staticmethod
    def assert_datetime_order(earlier: datetime,
                             later: datetime,
                             message: str = "") -> None:
        """Assert datetime ordering."""
        assert earlier <= later, \
            f"Expected {earlier} <= {later}. {message}"
    
    @staticmethod
    def assert_datetime_in_range(dt: datetime,
                                start: datetime,
                                end: datetime,
                                message: str = "") -> None:
        """Assert datetime is within range."""
        assert start <= dt <= end, \
            f"Datetime {dt} not in range [{start}, {end}]. {message}"


class BulkAssertions:
    """Assertions for bulk operations."""
    
    @staticmethod
    def assert_batch_operation_success(response_data: Dict[str, Any],
                                      expected_count: int,
                                      message: str = "") -> None:
        """Assert bulk operation processed expected number of records."""
        processed = response_data.get('processed', 0)
        assert processed == expected_count, \
            f"Expected {expected_count} records processed, got {processed}. {message}"
    
    @staticmethod
    def assert_no_duplicates(values: List[Any],
                            message: str = "") -> None:
        """Assert list contains no duplicates."""
        duplicates = [v for v in values if values.count(v) > 1]
        assert not duplicates, \
            f"Found duplicate values: {set(duplicates)}. {message}"
    
    @staticmethod
    def assert_list_subset(actual_list: List[Any],
                          expected_subset: List[Any],
                          message: str = "") -> None:
        """Assert actual list contains all expected items."""
        missing = [item for item in expected_subset if item not in actual_list]
        assert not missing, \
            f"Expected items not found: {missing}. {message}"


# Create convenience fixtures
@staticmethod
def create_assertions_fixture():
    """Create fixture providing all assertion classes."""
    return {
        'api': APIAssertions(),
        'db': DatabaseAssertions(),
        'decimal': DecimalAssertions(),
        'datetime': DateTimeAssertions(),
        'bulk': BulkAssertions(),
    }
