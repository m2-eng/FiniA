#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Factory Pattern for test data generation using factory-boy
#
from datetime import datetime, date, timedelta
from typing import Optional
import factory
from factory import Faker, LazyAttribute, SelfAttribute
import random
import string
from decimal import Decimal


class BaseFactory(factory.Factory):
    """Base factory with common settings"""
    class Meta:
        abstract = True
    
    dateImport = factory.LazyFunction(lambda: datetime.now())


class AccountFactory(BaseFactory):
    """Factory for creating test account records"""
    class Meta:
        # Note: This factory doesn't use ORM, custom save needed
        model = dict
    
    id = factory.Sequence(lambda n: n + 1000)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    name = factory.Faker('company')
    iban_accountNumber = factory.LazyAttribute(
        lambda o: 'DE' + ''.join(random.choices(string.digits, k=20))
    )
    bic_market = factory.LazyAttribute(
        lambda o: ''.join(random.choices(string.ascii_uppercase, k=8)))
    startAmount = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(100, 10000), 2))))
    dateStart = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(30, 365)))
    dateEnd = None
    type = factory.LazyFunction(lambda: random.randint(1, 5))  # Account types 1-5
    clearingAccount = None
    
    @classmethod
    def create_batch_sql(cls, cursor, count=5, **kwargs):
        """Create multiple accounts via SQL"""
        accounts = []
        for i in range(count):
            account = cls.build(dict, **kwargs)
            # Generate unique IBAN
            account['iban_accountNumber'] = f'DE{i:018d}'
            account['name'] = f"Test Account {i+1}"
            accounts.append(account)
        return accounts
    
    @staticmethod
    def insert_into_db(cursor, account_dict):
        """Insert account into test database"""
        sql = """
        INSERT INTO tbl_account 
        (id, dateImport, name, iban_accountNumber, bic_market, startAmount, 
         dateStart, dateEnd, type, clearingAccount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            account_dict['id'],
            account_dict['dateImport'],
            account_dict['name'],
            account_dict['iban_accountNumber'],
            account_dict['bic_market'],
            account_dict['startAmount'],
            account_dict['dateStart'],
            account_dict['dateEnd'],
            account_dict['type'],
            account_dict['clearingAccount']
        )
        cursor.execute(sql, params)
        return account_dict['id']


class AccountTypeFactory(BaseFactory):
    """Factory for account types"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 100 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    type = factory.Faker('word')
    
    @staticmethod
    def insert_into_db(cursor, account_type_dict):
        """Insert account type into database"""
        sql = """
        INSERT INTO tbl_accountType (id, dateImport, type)
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (
            account_type_dict['id'],
            account_type_dict['dateImport'],
            account_type_dict['type']
        ))
        return account_type_dict['id']


class CategoryFactory(BaseFactory):
    """Factory for creating category records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 2000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    name = factory.Faker('word')
    category = None  # Parent category (optional)
    
    @staticmethod
    def insert_into_db(cursor, category_dict):
        """Insert category into test database"""
        sql = """
        INSERT INTO tbl_category (id, dateImport, name, category)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (
            category_dict['id'],
            category_dict['dateImport'],
            category_dict['name'],
            category_dict['category']
        ))
        return category_dict['id']


class TransactionFactory(BaseFactory):
    """Factory for creating transaction records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 3000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    iban = factory.LazyAttribute(lambda o: 'DE' + ''.join(random.choices(string.digits, k=20)))
    bic = factory.Faker('swift')
    description = factory.Faker('sentence', nb_words=6)
    amount = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(-5000, 5000), 2))))
    dateValue = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 180)))
    recipientApplicant = factory.Faker('name')
    account = factory.LazyFunction(lambda: 1)  # Will be set to actual account_id
    
    @staticmethod
    def insert_into_db(cursor, transaction_dict):
        """Insert transaction into test database"""
        sql = """
        INSERT INTO tbl_transaction 
        (id, dateImport, iban, bic, description, amount, dateValue, 
         recipientApplicant, account)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            transaction_dict['id'],
            transaction_dict['dateImport'],
            transaction_dict['iban'],
            transaction_dict['bic'],
            transaction_dict['description'],
            transaction_dict['amount'],
            transaction_dict['dateValue'],
            transaction_dict['recipientApplicant'],
            transaction_dict['account']
        ))
        return transaction_dict['id']


class AccountingEntryFactory(BaseFactory):
    """Factory for creating accounting entry records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 4000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    checked = factory.LazyFunction(lambda: random.randint(0, 1))
    amount = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(-5000, 5000), 2))))
    transaction = factory.LazyFunction(lambda: 3000)  # Will be set to actual transaction_id
    accountingPlanned = None
    category = factory.LazyFunction(lambda: 2000)  # Will be set to actual category_id
    
    @staticmethod
    def insert_into_db(cursor, entry_dict):
        """Insert accounting entry into database"""
        sql = """
        INSERT INTO tbl_accountingEntry 
        (id, dateImport, checked, amount, transaction, accountingPlanned, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            entry_dict['id'],
            entry_dict['dateImport'],
            entry_dict['checked'],
            entry_dict['amount'],
            entry_dict['transaction'],
            entry_dict['accountingPlanned'],
            entry_dict['category']
        ))
        return entry_dict['id']


class PlanningCycleFactory(BaseFactory):
    """Factory for planning cycle records"""
    class Meta:
        model = dict
    
    CYCLE_CHOICES = [
        ('einmalig', 0.00, 'd'),
        ('täglich', 1.00, 'd'),
        ('wöchentlich', 7.00, 'd'),
        ('14-tägig', 14.00, 'd'),
        ('monatlich', 1.00, 'm'),
        ('vierteljährlich', 3.00, 'm'),
        ('halbjährlich', 6.00, 'm'),
        ('jährlich', 1.00, 'y'),
    ]
    
    id = factory.Sequence(lambda n: 5000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    cycle = factory.LazyFunction(lambda: random.choice([c[0] for c in PlanningCycleFactory.CYCLE_CHOICES]))
    periodValue = factory.LazyFunction(lambda: Decimal('1.00'))
    periodUnit = factory.LazyFunction(lambda: 'm')


class PlanningFactory(BaseFactory):
    """Factory for creating planning records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 6000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    description = factory.Faker('sentence', nb_words=4)
    amount = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(50, 1000), 2))))
    dateStart = factory.LazyFunction(lambda: datetime.now())
    dateEnd = None
    account = factory.LazyFunction(lambda: 1000)  # Will be set to actual account_id
    category = factory.LazyFunction(lambda: 2000)  # Will be set to actual category_id
    cycle = factory.LazyFunction(lambda: random.randint(1, 8))  # Planning cycle 1-8
    
    @staticmethod
    def insert_into_db(cursor, planning_dict):
        """Insert planning into database"""
        sql = """
        INSERT INTO tbl_planning 
        (id, dateImport, description, amount, dateStart, dateEnd, account, category, cycle)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            planning_dict['id'],
            planning_dict['dateImport'],
            planning_dict['description'],
            planning_dict['amount'],
            planning_dict['dateStart'],
            planning_dict['dateEnd'],
            planning_dict['account'],
            planning_dict['category'],
            planning_dict['cycle']
        ))
        return planning_dict['id']


class PlanningEntryFactory(BaseFactory):
    """Factory for planning entry records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 7000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    dateValue = factory.LazyFunction(lambda: datetime.now())
    planning = factory.LazyFunction(lambda: 6000)  # Will be set to actual planning_id
    
    @staticmethod
    def insert_into_db(cursor, entry_dict):
        """Insert planning entry into database"""
        sql = """
        INSERT INTO tbl_planningEntry (id, dateImport, dateValue, planning)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (
            entry_dict['id'],
            entry_dict['dateImport'],
            entry_dict['dateValue'],
            entry_dict['planning']
        ))
        return entry_dict['id']


class ShareFactory(BaseFactory):
    """Factory for creating share records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 8000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    name = factory.Faker('company')
    isin = factory.LazyAttribute(
        lambda o: 'DE' + ''.join(random.choices(string.digits + string.ascii_uppercase, k=10))
    )
    wkn = factory.LazyAttribute(lambda o: ''.join(random.choices(string.digits, k=6)))
    
    @staticmethod
    def insert_into_db(cursor, share_dict):
        """Insert share into database"""
        sql = """
        INSERT INTO tbl_share (id, dateImport, name, isin, wkn)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            share_dict['id'],
            share_dict['dateImport'],
            share_dict['name'],
            share_dict['isin'],
            share_dict['wkn']
        ))
        return share_dict['id']


class ShareHistoryFactory(BaseFactory):
    """Factory for share history records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 9000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    amount = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(0.01, 100), 2))))
    date = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 365)))
    checked = factory.LazyFunction(lambda: random.randint(0, 1))
    share = factory.LazyFunction(lambda: 8000)  # Will be set to actual share_id
    
    @staticmethod
    def insert_into_db(cursor, history_dict):
        """Insert share history into database"""
        sql = """
        INSERT INTO tbl_shareHistory (id, dateImport, amount, date, checked, share)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            history_dict['id'],
            history_dict['dateImport'],
            history_dict['amount'],
            history_dict['date'],
            history_dict['checked'],
            history_dict['share']
        ))
        return history_dict['id']


class ShareTransactionFactory(BaseFactory):
    """Factory for share transaction records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 10000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    tradingVolume = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(0.01, 500), 2))))
    dateTransaction = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 180)))
    checked = factory.LazyFunction(lambda: random.randint(0, 1))
    share = factory.LazyFunction(lambda: 8000)  # Will be set to actual share_id
    accountingEntry = None
    
    @staticmethod
    def insert_into_db(cursor, transaction_dict):
        """Insert share transaction into database"""
        sql = """
        INSERT INTO tbl_shareTransaction 
        (id, dateImport, tradingVolume, dateTransaction, checked, share, accountingEntry)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            transaction_dict['id'],
            transaction_dict['dateImport'],
            transaction_dict['tradingVolume'],
            transaction_dict['dateTransaction'],
            transaction_dict['checked'],
            transaction_dict['share'],
            transaction_dict['accountingEntry']
        ))
        return transaction_dict['id']


class LoanFactory(BaseFactory):
    """Factory for loan records"""
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: 11000 + n)
    dateImport = factory.LazyFunction(lambda: datetime.now())
    intrestRate = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(0.5, 5.0), 2))))
    account = factory.LazyFunction(lambda: 1000)  # Will be set to actual account_id
    categoryRebooking = None
    categoryIntrest = None
    
    @staticmethod
    def insert_into_db(cursor, loan_dict):
        """Insert loan into database"""
        sql = """
        INSERT INTO tbl_loan (id, dateImport, intrestRate, account, categoryRebooking, categoryIntrest)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            loan_dict['id'],
            loan_dict['dateImport'],
            loan_dict['intrestRate'],
            loan_dict['account'],
            loan_dict['categoryRebooking'],
            loan_dict['categoryIntrest']
        ))
        return loan_dict['id']
