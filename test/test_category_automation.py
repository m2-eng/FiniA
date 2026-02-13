#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Unit tests for Category Automation
#
"""
Unit tests for Category Automation

Tests the rule engine with:
- Condition logic parser (AND/OR/UND/ODER)
- Multiple conditions per rule
- Rule evaluation
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.category_automation import (
    parse_condition_logic,
    evaluate_condition,
    evaluate_rule
)
from datetime import datetime


class TestConditionLogicParser(unittest.TestCase):
    """Test the condition logic parser with various expressions"""
    
    def test_simple_or(self):
        """Test simple OR expression"""
        results = {1: True, 2: False}
        self.assertTrue(parse_condition_logic("1 OR 2", results))
        
        results = {1: False, 2: False}
        self.assertFalse(parse_condition_logic("1 OR 2", results))
    
    def test_simple_and(self):
        """Test simple AND expression"""
        results = {1: True, 2: True}
        self.assertTrue(parse_condition_logic("1 AND 2", results))
        
        results = {1: True, 2: False}
        self.assertFalse(parse_condition_logic("1 AND 2", results))
    
    def test_german_operators(self):
        """Test German operators UND/ODER"""
        results = {1: True, 2: False}
        self.assertTrue(parse_condition_logic("1 ODER 2", results))
        
        results = {1: True, 2: True}
        self.assertTrue(parse_condition_logic("1 UND 2", results))
        
        results = {1: False, 2: True}
        self.assertFalse(parse_condition_logic("1 UND 2", results))
    
    def test_mixed_german_english(self):
        """Test mixing German and English operators"""
        results = {1: True, 2: False, 3: True}
        self.assertTrue(parse_condition_logic("1 ODER 2 AND 3", results))
    
    def test_parentheses_simple(self):
        """Test simple parentheses grouping"""
        results = {1: False, 2: True, 3: True}
        self.assertTrue(parse_condition_logic("(1 OR 2) AND 3", results))
        
        results = {1: False, 2: False, 3: True}
        self.assertFalse(parse_condition_logic("(1 OR 2) AND 3", results))
    
    def test_nested_parentheses(self):
        """Test nested parentheses"""
        results = {1: True, 2: False, 3: True, 4: False}
        self.assertTrue(parse_condition_logic("(1 OR 2) AND (3 OR 4)", results))
        
        results = {1: False, 2: False, 3: True, 4: False}
        self.assertFalse(parse_condition_logic("(1 OR 2) AND (3 OR 4)", results))
    
    def test_complex_expression(self):
        """Test complex nested expression"""
        results = {1: True, 2: False, 3: True, 4: True, 5: False}
        # (True OR False OR True) AND (True OR False) = True AND True = True
        self.assertTrue(parse_condition_logic("(1 OR 2 OR 3) AND (4 OR 5)", results))
        
        results = {1: False, 2: False, 3: False, 4: True, 5: False}
        # (False OR False OR False) AND (True OR False) = False AND True = False
        self.assertFalse(parse_condition_logic("(1 OR 2 OR 3) AND (4 OR 5)", results))
    
    def test_three_way_or(self):
        """Test three conditions with OR"""
        results = {1: False, 2: False, 3: True}
        self.assertTrue(parse_condition_logic("1 OR 2 OR 3", results))
    
    def test_three_way_and(self):
        """Test three conditions with AND"""
        results = {1: True, 2: True, 3: True}
        self.assertTrue(parse_condition_logic("1 AND 2 AND 3", results))
        
        results = {1: True, 2: False, 3: True}
        self.assertFalse(parse_condition_logic("1 AND 2 AND 3", results))
    
    def test_empty_logic(self):
        """Test with null/empty logic (should default to OR all)"""
        results = {1: False, 2: True, 3: False}
        self.assertTrue(parse_condition_logic(None, results))
        self.assertTrue(parse_condition_logic("", results))
        
        results = {1: False, 2: False, 3: False}
        self.assertFalse(parse_condition_logic(None, results))
    
    def test_single_condition(self):
        """Test with single condition"""
        results = {1: True}
        self.assertTrue(parse_condition_logic("1", results))
        
        results = {1: False}
        self.assertFalse(parse_condition_logic("1", results))
    
    def test_case_insensitive(self):
        """Test case insensitivity of operators"""
        results = {1: True, 2: False}
        self.assertTrue(parse_condition_logic("1 or 2", results))
        self.assertTrue(parse_condition_logic("1 Or 2", results))
        self.assertTrue(parse_condition_logic("1 oDeR 2", results))


class TestConditionEvaluation(unittest.TestCase):
    """Test evaluation of individual conditions"""
    
    def test_contains_match(self):
        """Test contains condition - matching"""
        condition = {
            'id': 1,
            'type': 'contains',
            'columnName': 'description',
            'value': 'MIETE',
            'caseSensitive': False
        }
        transaction = {
            'description': 'Zahlung MIETE Wohnung Januar',
            'amount': -800.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
    
    def test_contains_no_match(self):
        """Test contains condition - not matching"""
        condition = {
            'id': 1,
            'type': 'contains',
            'columnName': 'description',
            'value': 'MIETE',
            'caseSensitive': False
        }
        transaction = {
            'description': 'Supermarkt REWE',
            'amount': -50.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_contains_case_sensitive(self):
        """Test contains with case sensitivity"""
        condition = {
            'id': 1,
            'type': 'contains',
            'columnName': 'description',
            'value': 'MIETE',
            'caseSensitive': True
        }
        transaction = {
            'description': 'Zahlung miete Wohnung',  # lowercase
            'amount': -800.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_equals_match(self):
        """Test equals condition"""
        condition = {
            'id': 1,
            'type': 'equals',
            'columnName': 'description',
            'value': 'MIETE',
            'caseSensitive': False
        }
        transaction = {
            'description': 'MIETE',
            'amount': -800.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
        
        transaction = {
            'description': 'MIETE Januar',
            'amount': -800.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_starts_with(self):
        """Test startsWith condition"""
        condition = {
            'id': 1,
            'type': 'startsWith',
            'columnName': 'description',
            'value': 'Amazon',
            'caseSensitive': False
        }
        transaction = {
            'description': 'Amazon.de Order 123',
            'amount': -50.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
        
        transaction = {
            'description': 'Prime Amazon Order',
            'amount': -50.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_ends_with(self):
        """Test endsWith condition"""
        condition = {
            'id': 1,
            'type': 'endsWith',
            'columnName': 'description',
            'value': 'GmbH',
            'caseSensitive': False
        }
        transaction = {
            'description': 'Example Company GmbH',
            'amount': -100.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
    
    def test_regex_match(self):
        """Test regex condition"""
        condition = {
            'id': 1,
            'type': 'regex',
            'columnName': 'description',
            'value': r'^[A-Z]{2}\d{2}',  # Two letters, two digits
            'caseSensitive': True
        }
        transaction = {
            'description': 'AB12 Payment',
            'amount': -50.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
        
        transaction = {
            'description': 'ABC123 Payment',
            'amount': -50.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_amount_range_within(self):
        """Test amountRange condition - amount within range"""
        condition = {
            'id': 1,
            'type': 'amountRange',
            'columnName': 'amount',
            'minAmount': -1000.0,
            'maxAmount': -800.0
        }
        transaction = {
            'description': 'Rent',
            'amount': -900.0
        }
        self.assertTrue(evaluate_condition(transaction, condition))
    
    def test_amount_range_below(self):
        """Test amountRange condition - amount below range"""
        condition = {
            'id': 1,
            'type': 'amountRange',
            'columnName': 'amount',
            'minAmount': -1000.0,
            'maxAmount': -800.0
        }
        transaction = {
            'description': 'Rent',
            'amount': -1200.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_amount_range_above(self):
        """Test amountRange condition - amount above range"""
        condition = {
            'id': 1,
            'type': 'amountRange',
            'columnName': 'amount',
            'minAmount': -1000.0,
            'maxAmount': -800.0
        }
        transaction = {
            'description': 'Rent',
            'amount': -700.0
        }
        self.assertFalse(evaluate_condition(transaction, condition))
    
    def test_amount_range_boundary(self):
        """Test amountRange at boundaries"""
        condition = {
            'id': 1,
            'type': 'amountRange',
            'columnName': 'amount',
            'minAmount': -1000.0,
            'maxAmount': -800.0
        }
        # Test min boundary
        transaction = {'description': 'Test', 'amount': -1000.0}
        self.assertTrue(evaluate_condition(transaction, condition))
        
        # Test max boundary
        transaction = {'description': 'Test', 'amount': -800.0}
        self.assertTrue(evaluate_condition(transaction, condition))
    
    def test_missing_column(self):
        """Test condition when column is missing from transaction"""
        condition = {
            'id': 1,
            'type': 'contains',
            'columnName': 'recipientApplicant',
            'value': 'John Doe'
        }
        transaction = {
            'description': 'Payment',
            'amount': -50.0
            # recipientApplicant missing
        }
        self.assertFalse(evaluate_condition(transaction, condition))


class TestRuleEvaluation(unittest.TestCase):
    """Test evaluation of complete rules with multiple conditions"""
    
    def test_single_condition_match(self):
        """Test rule with single condition - matching"""
        rule = {
            'id': 'test-rule-1',
            'name': 'Rent',
            'conditions': [{
                'id': 1,
                'type': 'contains',
                'columnName': 'description',
                'value': 'MIETE',
                'caseSensitive': False
            }],
            'conditionLogic': None,
            'category': 123
        }
        transaction = {
            'description': 'Zahlung MIETE Januar',
            'amount': -800.0
        }
        self.assertTrue(evaluate_rule(transaction, rule))
    
    def test_or_logic_one_match(self):
        """Test OR logic with one condition matching"""
        rule = {
            'id': 'test-rule-2',
            'name': 'Rent with typos',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'MIETE', 'caseSensitive': False},
                {'id': 2, 'type': 'contains', 'columnName': 'description', 'value': 'MITE', 'caseSensitive': False},
                {'id': 3, 'type': 'contains', 'columnName': 'description', 'value': 'RENT', 'caseSensitive': False}
            ],
            'conditionLogic': '1 OR 2 OR 3',
            'category': 123
        }
        transaction = {
            'description': 'Zahlung MITE Januar',  # Typo
            'amount': -800.0
        }
        self.assertTrue(evaluate_rule(transaction, rule))
    
    def test_or_logic_no_match(self):
        """Test OR logic with no conditions matching"""
        rule = {
            'id': 'test-rule-3',
            'name': 'Rent variations',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'MIETE', 'caseSensitive': False},
                {'id': 2, 'type': 'contains', 'columnName': 'description', 'value': 'RENT', 'caseSensitive': False}
            ],
            'conditionLogic': '1 OR 2',
            'category': 123
        }
        transaction = {
            'description': 'Supermarkt REWE',
            'amount': -50.0
        }
        self.assertFalse(evaluate_rule(transaction, rule))
    
    def test_and_logic_all_match(self):
        """Test AND logic with all conditions matching"""
        rule = {
            'id': 'test-rule-4',
            'name': 'Salary with amount check',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'GEHALT', 'caseSensitive': False},
                {'id': 2, 'type': 'amountRange', 'columnName': 'amount', 'minAmount': 2000.0, 'maxAmount': 5000.0}
            ],
            'conditionLogic': '1 AND 2',
            'category': 234
        }
        transaction = {
            'description': 'GEHALT Januar',
            'amount': 3000.0
        }
        self.assertTrue(evaluate_rule(transaction, rule))
    
    def test_and_logic_partial_match(self):
        """Test AND logic with only one condition matching"""
        rule = {
            'id': 'test-rule-5',
            'name': 'Salary with amount check',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'GEHALT', 'caseSensitive': False},
                {'id': 2, 'type': 'amountRange', 'columnName': 'amount', 'minAmount': 2000.0, 'maxAmount': 5000.0}
            ],
            'conditionLogic': '1 AND 2',
            'category': 234
        }
        # Description matches but amount doesn't
        transaction = {
            'description': 'GEHALT Bonus',
            'amount': 6000.0
        }
        self.assertFalse(evaluate_rule(transaction, rule))
    
    def test_complex_nested_logic(self):
        """Test complex nested logic (OR AND OR)"""
        rule = {
            'id': 'test-rule-6',
            'name': 'Groceries with amount filter',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'REWE', 'caseSensitive': False},
                {'id': 2, 'type': 'contains', 'columnName': 'description', 'value': 'EDEKA', 'caseSensitive': False},
                {'id': 3, 'type': 'contains', 'columnName': 'description', 'value': 'ALDI', 'caseSensitive': False},
                {'id': 4, 'type': 'amountRange', 'columnName': 'amount', 'minAmount': -200.0, 'maxAmount': -50.0}
            ],
            'conditionLogic': '(1 OR 2 OR 3) AND 4',
            'category': 345
        }
        # ALDI + amount in range
        transaction = {
            'description': 'ALDI SÜD Einkauf',
            'amount': -75.0
        }
        self.assertTrue(evaluate_rule(transaction, rule))
        
        # ALDI but amount too small
        transaction = {
            'description': 'ALDI SÜD Snack',
            'amount': -10.0
        }
        self.assertFalse(evaluate_rule(transaction, rule))
    
    def test_default_or_logic(self):
        """Test default OR logic when conditionLogic is None"""
        rule = {
            'id': 'test-rule-7',
            'name': 'Multiple options',
            'conditions': [
                {'id': 1, 'type': 'contains', 'columnName': 'description', 'value': 'OPTION1', 'caseSensitive': False},
                {'id': 2, 'type': 'contains', 'columnName': 'description', 'value': 'OPTION2', 'caseSensitive': False}
            ],
            'conditionLogic': None,  # Should default to OR
            'category': 456
        }
        transaction = {
            'description': 'Test OPTION2',
            'amount': -100.0
        }
        self.assertTrue(evaluate_rule(transaction, rule))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
