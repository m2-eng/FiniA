"""
Category automation utilities - rule evaluation and application logic

Features:
- Multiple conditions per rule
- Flexible condition logic (AND/OR/UND/ODER)
- Multiple accounts per rule
- Rule descriptions
- Settings-based storage (tbl_setting)
"""

import json
import re
from typing import Optional, Dict, List, Any

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


def parse_condition_logic(logic_str: str, condition_results: Dict[int, bool]) -> bool:
    """
    Parse and evaluate condition logic expression.
    
    Supports:
    - AND, OR operators (English)
    - UND, ODER operators (German)
    - Parentheses for grouping
    - Condition IDs (integers)
    
    Args:
        logic_str: Expression like "(1 OR 3) AND 2" or "(1 ODER 3) UND 2"
        condition_results: Dict mapping condition ID to boolean result
        
    Returns:
        Boolean result of expression
        
    Examples:
        >>> parse_condition_logic("1 OR 2", {1: True, 2: False})
        True
        >>> parse_condition_logic("(1 OR 2) AND 3", {1: False, 2: True, 3: True})
        True
        >>> parse_condition_logic("1 UND 2", {1: True, 2: False})
        False
    """
    if not logic_str or not condition_results:
        # Fallback: OR all conditions
        return any(condition_results.values())
    
    try:
        # Normalize: German → English
        normalized = logic_str.upper()
        normalized = normalized.replace(' UND ', ' AND ')
        normalized = normalized.replace(' ODER ', ' OR ')
        normalized = normalized.replace(' NICHT ', ' NOT ')
        
        # Replace condition IDs with their boolean results
        for cond_id, result in condition_results.items():
            # Use word boundaries to avoid partial replacements (e.g., 1 in 10)
            # Replace with capitalized True/False for Python eval
            normalized = re.sub(
                rf'\b{cond_id}\b',
                str(result),  # Python's str(True) = "True", str(False) = "False"
                normalized
            )
        
        # Evaluate as Python expression
        # After replacement we have: "(True OR False) AND True"
        # Convert operators to Python syntax
        normalized = normalized.replace(' AND ', ' and ')
        normalized = normalized.replace(' OR ', ' or ')
        normalized = normalized.replace(' NOT ', ' not ')
        
        return eval(normalized)
        
    except Exception as e:
        # Fallback on error: OR all conditions
        print(f"Warning: Failed to parse condition logic '{logic_str}': {e}")
        return any(condition_results.values())


def evaluate_condition(transaction_data: Dict, condition: Dict) -> bool:
    """
    Evaluate a single condition against transaction data.
    
    Args:
        transaction_data: Transaction dict with keys: description, recipientApplicant, amount, iban
        condition: Single condition dict with keys: id, type, columnName, value, caseSensitive, minAmount, maxAmount
        
    Returns:
        True if condition matches, False otherwise
    """
    column_name = condition.get('columnName')
    tx_value = transaction_data.get(column_name)
    
    if tx_value is None:
        return False
    
    cond_type = condition.get('type', 'contains')
    
    # Amount-based conditions
    if cond_type == 'amountRange':
        try:
            tx_amount = float(tx_value)
            min_amount = condition.get('minAmount')
            max_amount = condition.get('maxAmount')
            
            if min_amount is not None and tx_amount < min_amount:
                return False
            if max_amount is not None and tx_amount > max_amount:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    # String-based conditions
    tx_str = str(tx_value)
    rule_value = condition.get('value', '')
    case_sensitive = condition.get('caseSensitive', False)
    
    if not case_sensitive:
        tx_str = tx_str.lower()
        rule_value = rule_value.lower() if rule_value else ''
    
    return _evaluate_string_rule(tx_str, rule_value, cond_type, case_sensitive)


def evaluate_rule(transaction_data: Dict, rule: Dict) -> bool:
    """
    Evaluate if a transaction matches an automation rule.
    
    Args:
        transaction_data: Transaction dict with keys: description, recipientApplicant, amount, iban
        rule: Rule dict with conditions and conditionLogic
        
    Returns:
        True if rule matches, False otherwise
    """
    conditions = rule.get('conditions', [])
    if not conditions:
        return False
    
    # Evaluate each condition
    condition_results = {}
    for condition in conditions:
        cond_id = condition.get('id')
        if cond_id is not None:
            condition_results[cond_id] = evaluate_condition(transaction_data, condition)
    
    # Apply condition logic
    logic_str = rule.get('conditionLogic')
    if logic_str:
        return parse_condition_logic(logic_str, condition_results)
    else:
        # Default: OR all conditions
        return any(condition_results.values())


def load_rules(cursor, account_id: Optional[int] = None) -> List[Dict]:
    """
    Load automation rules from tbl_setting.
    
    Args:
        cursor: Database cursor
        account_id: Optional account ID to filter rules
        
    Returns:
        List of rule dicts, sorted by priority (descending)
    """
    query = """
        SELECT id, value
        FROM tbl_setting
        WHERE `key` = 'category_automation_rule'
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        rules = []
        for row in rows:
            try:
                rule = json.loads(row[1])  # value is JSON
                
                # Skip disabled rules
                if not rule.get('enabled', True):
                    continue
                
                # Filter by account if specified
                if account_id is not None:
                    rule_accounts = rule.get('accounts', [])
                    # Empty accounts array = applies to all accounts
                    if rule_accounts and account_id not in rule_accounts:
                        continue
                
                rules.append(rule)
                
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Failed to parse rule {row[0]}: {e}")
                continue
        
        # Sort by priority descending, then by dateCreated
        rules.sort(
            key=lambda r: (
                r.get('priority', 5),
                r.get('dateCreated', '')
            ),
            reverse=True
        )
        
        return rules
        
    except Exception as e:
        print(f"Error loading automation rules: {e}")
        return []


def apply_rules_to_transaction(
    transaction_data: Dict,
    rules: List[Dict]
) -> Optional[int]:
    """
    Apply automation rules to a transaction and return category ID if matched.
    
    Args:
        transaction_data: Transaction dict with keys: description, recipientApplicant, amount, iban
        rules: List of rule dicts (already filtered and sorted)
        
    Returns:
        Category ID if a rule matches, None otherwise
    """
    for rule in rules:
        if evaluate_rule(transaction_data, rule):
            return rule.get('category')
    
    return None
