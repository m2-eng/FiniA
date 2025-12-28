"""
Category automation utilities - shared rule evaluation and application logic
"""

import json
import re
from typing import Optional, Dict, List, Tuple


def evaluate_rule(transaction_data: Dict, rule_record: Tuple) -> bool:
    """
    Evaluate if a transaction matches an automation rule.
    
    Args:
        transaction_data: Transaction dict with keys: description, recipientApplicant, amount, iban
        rule_record: Tuple from database with (columnName, rule_json)
        
    Returns:
        True if rule matches, False otherwise
    """
    if not rule_record or len(rule_record) < 2:
        return False
    
    column_name = rule_record[0]  # columnName
    rule_json_str = rule_record[1]  # rule JSON
    
    try:
        rule_def = json.loads(rule_json_str)
    except (json.JSONDecodeError, TypeError):
        return False
    
    # Get value from transaction
    tx_value = transaction_data.get(column_name)
    if tx_value is None:
        return False
    
    rule_type = rule_def.get("type", "contains")
    rule_value = rule_def.get("value")
    case_sensitive = rule_def.get("caseSensitive", False)
    
    # Handle different column types
    if column_name == "amount":
        return _evaluate_amount_rule(float(tx_value), rule_def, rule_type)
    else:
        # String comparison
        tx_str = str(tx_value)
        if not case_sensitive:
            tx_str = tx_str.lower()
            rule_value = rule_value.lower() if rule_value else ""
        
        return _evaluate_string_rule(tx_str, rule_value, rule_type, case_sensitive)


def _evaluate_string_rule(tx_value: str, rule_value: str, rule_type: str, case_sensitive: bool) -> bool:
    """Evaluate string-based rules"""
    if rule_type == "contains":
        return rule_value in tx_value if rule_value else False
    
    elif rule_type == "equals":
        return tx_value == rule_value
    
    elif rule_type == "startsWith":
        return tx_value.startswith(rule_value) if rule_value else False
    
    elif rule_type == "endsWith":
        return tx_value.endswith(rule_value) if rule_value else False
    
    elif rule_type == "regex":
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            return bool(re.search(rule_value, tx_value, flags))
        except re.error:
            return False
    
    return False


def _evaluate_amount_rule(tx_amount: float, rule_def: Dict, rule_type: str) -> bool:
    """Evaluate amount-based rules"""
    if rule_type == "amountRange":
        min_amount = rule_def.get("minAmount")
        max_amount = rule_def.get("maxAmount")
        
        if min_amount is not None and tx_amount < min_amount:
            return False
        if max_amount is not None and tx_amount > max_amount:
            return False
        return True
    
    return False


def apply_rules_to_transaction(
    transaction_data: Dict,
    rules_list: List[Tuple],
    account_id: int
) -> Optional[int]:
    """
    Apply automation rules to a transaction and return category ID if matched.
    Rules are evaluated in priority order (highest first).
    
    Args:
        transaction_data: Transaction dict with keys: description, recipientApplicant, amount, iban
        rules_list: List of rule records (columnName, rule_json, category_id, account_id, priority)
        account_id: The account ID to filter rules for
        
    Returns:
        Category ID if a rule matches, None otherwise
    """
    if not rules_list:
        return None
    
    # Filter and sort rules by priority (highest first)
    matching_rules = [
        rule for rule in rules_list
        if rule[3] == account_id  # rule[3] is account_id
    ]
    
    if not matching_rules:
        return None
    
    # Sort by priority descending (handle None values by treating them as 0)
    matching_rules.sort(key=lambda r: (r[4] is not None, r[4] or 0), reverse=True)
    
    # Test each rule in order
    for rule in matching_rules:
        # rule tuple: (columnName, rule_json, category_id, account_id, priority)
        if evaluate_rule(transaction_data, (rule[0], rule[1])):
            return rule[2]  # Return category_id
    
    return None


def get_all_account_rules(cursor) -> List[Tuple]:
    """
    Fetch all active automation rules from database.
    
    Returns:
        List of tuples: (columnName, rule_json, category_id, account_id, priority)
    """
    query = """
        SELECT columnName, rule, category, account, 
               COALESCE(JSON_EXTRACT(rule, '$.priority'), 1) as priority
        FROM tbl_categoryAutomation
        ORDER BY COALESCE(JSON_EXTRACT(rule, '$.priority'), 1) DESC, id ASC
    """
    
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching automation rules: {e}")
        return []
