#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Faker-based test data generators for comprehensive test scenarios
#
from faker import Faker
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string


class TestDataGenerator:
    """Generate realistic test data using Faker"""
    
    def __init__(self, locale='de_DE'):
        self.faker = Faker(locale)
        self._id_counter = {}
    
    def get_next_id(self, entity: str) -> int:
        """Get next available ID for entity type"""
        if entity not in self._id_counter:
            self._id_counter[entity] = 1000
        self._id_counter[entity] += 1
        return self._id_counter[entity]
    
    # ========================================
    # ACCOUNT DATA GENERATORS
    # ========================================
    
    def generate_account_data(self, 
                             account_type: int = 1,
                             start_amount: float = None,
                             include_end_date: bool = False) -> dict:
        """Generate realistic account data"""
        if start_amount is None:
            start_amount = round(random.uniform(1000, 100000), 2)
        
        date_start = self.faker.date_between(start_date='-5y')
        date_end = date_start + timedelta(days=random.randint(365, 1825)) if include_end_date else None
        
        return {
            'name': self.faker.company(),
            'iban_accountNumber': self.faker.iban(),
            'bic_market': self.faker.swift(),
            'startAmount': Decimal(str(round(start_amount, 2))),
            'dateStart': datetime.combine(date_start, datetime.min.time()),
            'dateEnd': datetime.combine(date_end, datetime.min.time()) if date_end else None,
            'type': account_type,
            'clearingAccount': None
        }
    
    def generate_account_batch(self, count: int = 5, **kwargs) -> list:
        """Generate multiple accounts"""
        return [self.generate_account_data(**kwargs) for _ in range(count)]
    
    # ========================================
    # CATEGORY DATA GENERATORS
    # ========================================
    
    def generate_category_data(self, parent_id: int = None, depth: int = 0) -> dict:
        """Generate category data with optional hierarchy"""
        CATEGORY_TEMPLATES = [
            'Lebensmittel', 'Wohnung', 'Transport', 'Gesundheit', 'Unterhaltung',
            'Versicherung', 'Steuern', 'Bildung', 'Kleidung', 'Reisen'
        ]
        
        base_name = random.choice(CATEGORY_TEMPLATES)
        if depth > 0:
            base_name = f"{base_name} - {self.faker.word()}"
        
        return {
            'name': base_name,
            'category': parent_id
        }
    
    def generate_category_hierarchy(self, depth: int = 2) -> list:
        """Generate category hierarchy (parent -> children -> grandchildren)"""
        categories = []
        parent_id = None
        
        for level in range(depth):
            for _ in range(2):  # 2 categories per level
                category = self.generate_category_data(parent_id=parent_id, depth=level)
                parent_id = category  # Use dict as reference (will have ID added)
                categories.append(category)
        
        return categories
    
    # ========================================
    # TRANSACTION DATA GENERATORS
    # ========================================
    
    def generate_transaction_data(self, 
                                 account_id: int,
                                 amount: float = None,
                                 days_back: int = 180) -> dict:
        """Generate transaction data"""
        if amount is None:
            # 70% expenses (negative), 30% income (positive)
            is_expense = random.random() < 0.7
            amount_value = random.uniform(10, 2000)
            amount = -amount_value if is_expense else amount_value
        
        return {
            'iban': self.faker.iban(),
            'bic': self.faker.swift(),
            'description': self.faker.bulky_word(),
            'amount': Decimal(str(round(amount, 2))),
            'dateValue': datetime.combine(
                self.faker.date_between(start_date=f'-{days_back}d'),
                datetime.min.time()
            ),
            'recipientApplicant': self.faker.name(),
            'account': account_id
        }
    
    def generate_transaction_batch(self, 
                                  account_id: int,
                                  count: int = 10,
                                  spread_days: int = 180) -> list:
        """Generate multiple transactions for a period"""
        return [
            self.generate_transaction_data(account_id, days_back=spread_days)
            for _ in range(count)
        ]
    
    def generate_expense_sequence(self,
                                account_id: int,
                                category: str = 'Groceries',
                                start_date=None,
                                monthly_amount: float = 500) -> list:
        """Generate sequence of similar expenses (like monthly costs)"""
        transactions = []
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        
        for month_offset in range(12):
            trans_date = start_date + timedelta(days=30 * month_offset)
            variation = round(monthly_amount * random.uniform(0.8, 1.2), 2)
            
            transactions.append({
                'description': f'{category} - recurring',
                'amount': Decimal(str(-variation)),
                'dateValue': trans_date,
                'recipientApplicant': category,
                'account': account_id,
                'iban': None,
                'bic': None
            })
        
        return transactions
    
    # ========================================
    # PLANNING DATA GENERATORS
    # ========================================
    
    def generate_planning_data(self,
                              account_id: int,
                              category_id: int,
                              cycle_id: int = 5,  # Monthly default
                              amount: float = None) -> dict:
        """Generate planning data"""
        if amount is None:
            amount = round(random.uniform(50, 500), 2)
        
        return {
            'description': self.faker.sentence(nb_words=5),
            'amount': Decimal(str(amount)),
            'dateStart': datetime.combine(
                self.faker.date_between(start_date='-1y'),
                datetime.min.time()
            ),
            'dateEnd': None,
            'account': account_id,
            'category': category_id,
            'cycle': cycle_id
        }
    
    def generate_planning_batch(self,
                               account_id: int,
                               category_ids: list,
                               count: int = None) -> list:
        """Generate multiple planning entries"""
        if count is None:
            count = min(len(category_ids), 5)
        
        return [
            self.generate_planning_data(
                account_id,
                random.choice(category_ids)
            )
            for _ in range(count)
        ]
    
    # ========================================
    # SHARE DATA GENERATORS
    # ========================================
    
    def generate_share_data(self) -> dict:
        """Generate share/security data"""
        return {
            'name': self.faker.company(),
            'isin': self._generate_isin(),
            'wkn': self._generate_wkn()
        }
    
    def generate_share_batch(self, count: int = 5) -> list:
        """Generate multiple shares"""
        return [self.generate_share_data() for _ in range(count)]
    
    def _generate_isin(self) -> str:
        """Generate valid ISIN format (2 letter country + 9 digit code + 1 check digit)"""
        country = random.choice(['DE', 'US', 'FR', 'GB', 'CH'])
        code = ''.join(random.choices(string.digits, k=9))
        check_digit = random.randint(0, 9)
        return f"{country}{code}{check_digit}"
    
    def _generate_wkn(self) -> str:
        """Generate valid WKN format (6 digits/letters)"""
        return ''.join(random.choices(string.digits + string.ascii_uppercase, k=6))
    
    def generate_share_history_data(self, share_id: int, days_back: int = 365) -> dict:
        """Generate share price history"""
        return {
            'amount': Decimal(str(round(random.uniform(0.01, 500), 2))),
            'date': datetime.combine(
                self.faker.date_between(start_date=f'-{days_back}d'),
                datetime.min.time()
            ),
            'checked': random.randint(0, 1),
            'share': share_id
        }
    
    def generate_share_history_batch(self,
                                    share_id: int,
                                    count: int = 12) -> list:
        """Generate share price history (e.g., monthly prices)"""
        return [
            self.generate_share_history_data(share_id)
            for _ in range(count)
        ]
    
    def generate_share_transaction_data(self,
                                       share_id: int,
                                       trading_volume: float = None) -> dict:
        """Generate share transaction data"""
        if trading_volume is None:
            trading_volume = round(random.uniform(0.01, 100), 2)
        
        return {
            'tradingVolume': Decimal(str(trading_volume)),
            'dateTransaction': datetime.combine(
                self.faker.date_between(start_date='-2y'),
                datetime.min.time()
            ),
            'checked': random.randint(0, 1),
            'share': share_id,
            'accountingEntry': None
        }
    
    # ========================================
    # BULK DATA GENERATION
    # ========================================
    
    def generate_complete_dataset(self,
                                 num_accounts: int = 3,
                                 transactions_per_account: int = 50,
                                 categories: int = 10) -> dict:
        """Generate complete dataset for integration tests"""
        accounts = []
        categories = []
        transactions = []
        planning = []
        
        # Generate accounts
        account_ids = []
        for i in range(num_accounts):
            acc = self.generate_account_data()
            acc['id'] = self.get_next_id('account')
            account_ids.append(acc['id'])
            accounts.append(acc)
        
        # Generate categories
        category_ids = []
        for i in range(categories):
            cat = self.generate_category_data()
            cat['id'] = self.get_next_id('category')
            category_ids.append(cat['id'])
            categories.append(cat)
        
        # Generate transactions
        for acc_id in account_ids:
            trans = self.generate_transaction_batch(acc_id, count=transactions_per_account)
            transactions.extend(trans)
        
        # Generate planning
        for acc_id in account_ids:
            plan = self.generate_planning_batch(acc_id, category_ids, count=5)
            planning.extend(plan)
        
        return {
            'accounts': accounts,
            'categories': categories,
            'transactions': transactions,
            'planning': planning
        }
    
    # ========================================
    # EDGE CASE DATA GENERATORS
    # ========================================
    
    def generate_boundary_transaction(self, 
                                     account_id: int,
                                     boundary_type: str = 'max_positive') -> dict:
        """Generate boundary value transactions for edge case testing"""
        boundaries = {
            'max_positive': 999999999.99,
            'min_negative': -999999999.99,
            'zero': 0.00,
            'very_small': 0.01,
            'very_large': 999999.99
        }
        
        amount = boundaries.get(boundary_type, 0.00)
        return self.generate_transaction_data(account_id, amount=amount)
    
    def generate_duplicate_transaction(self, 
                                       account_id: int,
                                       base_transaction: dict = None) -> dict:
        """Generate near-duplicate transaction for duplicate detection testing"""
        if base_transaction is None:
            base_transaction = self.generate_transaction_data(account_id)
        
        # Create slightly modified duplicate
        duplicate = base_transaction.copy()
        duplicate['dateValue'] = base_transaction['dateValue'] + timedelta(days=1)
        return duplicate
    
    def generate_invalid_data_cases(self) -> dict:
        """Generate test cases for invalid data scenarios"""
        return {
            'negative_start_amount': {
                'startAmount': Decimal('-1000.00'),
                'note': 'Accounts should not have negative starting amount'
            },
            'future_start_date': {
                'dateStart': datetime.now() + timedelta(days=365),
                'note': 'Account start date should not be in future'
            },
            'end_before_start': {
                'dateStart': datetime.now(),
                'dateEnd': datetime.now() - timedelta(days=1),
                'note': 'End date should not be before start date'
            },
            'zero_transaction': {
                'amount': Decimal('0.00'),
                'note': 'Zero transactions should be handled'
            },
            'invalid_iban': {
                'iban_accountNumber': 'INVALID',
                'note': 'Invalid IBAN format'
            }
        }
