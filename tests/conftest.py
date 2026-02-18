"""
Pytest Configuration and Shared Fixtures for FiniA Test Suite.
Issue #32: Implementing a test bench

This module provides:
- Database connection management
- Test user configuration
- API client setup
- Cleanup fixtures
- Assertion helpers
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Generator, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import pytest
import requests
import yaml
from dotenv import load_dotenv

# Load test environment
env_file = Path(__file__).parent.parent / ".env.test"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TEST USER MANAGEMENT (Task 1.3)
# ============================================================================

@dataclass
class TestUser:
    """Test user configuration."""
    username: str
    password: str
    description: str
    user_type: str
    permissions: list
    skip_teardown: bool


def load_test_users() -> Dict[str, TestUser]:
    """Load test users from cfg/test_users.yaml"""
    config_path = Path(__file__).parent.parent / "cfg" / "test_users.yaml"
    
    if not config_path.exists():
        logger.warning(f"Test users config not found: {config_path}")
        return {}
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    users = {}
    for user_id, user_data in config.get('test_users', {}).items():
        users[user_id] = TestUser(
            username=user_data['username'],
            password=user_data['password'],
            description=user_data['description'],
            user_type=user_data['type'],
            permissions=user_data['permissions'],
            skip_teardown=user_data.get('skip_teardown', False)
        )
    return users


ALL_TEST_USERS = load_test_users()
DEFAULT_TEST_USER = os.getenv('FINIA_TEST_USER', 'local_test')


@pytest.fixture(scope='session')
def test_config() -> Dict[str, Any]:
    """Load test configuration from environment."""
    return {
        'api_base_url': os.getenv('TEST_API_BASE_URL', 'http://localhost:8000'),
        'api_timeout': int(os.getenv('TEST_API_TIMEOUT', '30')),
        'db_host': os.getenv('DB_TEST_HOST', '127.0.0.1'),
        'db_port': int(os.getenv('DB_TEST_PORT', '3306')),
        'db_user': os.getenv('DB_TEST_USER', 'root'),
        'db_password': os.getenv('DB_TEST_PASSWORD', ''),
        'db_name': os.getenv('DB_TEST_NAME', 'finia_test'),
        'test_user': os.getenv('FINIA_TEST_USER', DEFAULT_TEST_USER),
        'report_dir': Path(os.getenv('REPORT_OUTPUT_DIR', './tests/reports')),
    }


@pytest.fixture(scope='session')
def current_test_user(test_config) -> TestUser:
    """Get the current test user."""
    user_id = test_config['test_user']
    if user_id not in ALL_TEST_USERS:
        raise ValueError(f"Test user '{user_id}' not found in test_users.yaml")
    return ALL_TEST_USERS[user_id]


# ============================================================================
# DATABASE FIXTURES (Task 1.4)
# ============================================================================

@pytest.fixture(scope='function')
def db_connection(test_config):
    """Function-scoped database connection for serial test execution."""
    import mysql.connector
    
    conn = None
    try:
        conn = mysql.connector.connect(
            host=test_config['db_host'],
            port=test_config['db_port'],
            user=test_config['db_user'],
            password=test_config['db_password'],
            database=test_config['db_name'],
            autocommit=False  # Explicit transaction control
        )
        logger.debug(f"✓ Connected to test database: {test_config['db_name']}")
        yield conn
    except Exception as e:
        logger.error(f"✗ Failed to connect to test database: {e}")
        raise
    finally:
        if conn and conn.is_connected():
            try:
                conn.rollback()  # Rollback any uncommitted changes
                conn.close()
                logger.debug("✓ Database connection closed")
            except Exception as e:
                logger.warning(f"Warning closing connection: {e}")


@pytest.fixture(scope='function')
def db_cursor(db_connection):
    """Function-scoped cursor with cleanup."""
    cursor = None
    try:
        cursor = db_connection.cursor()
        yield cursor
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass  # Ignore errors on close


@pytest.fixture(scope='function', autouse=True)
def cleanup_test_data(db_cursor, db_connection, current_test_user):
    """Auto-cleanup test data after each test (unless skip_teardown=True)."""
    yield
    
    if current_test_user.skip_teardown:
        logger.info("Skipping teardown for performance test data")
        return
    
    # Cleanup strategy: Delete in reverse dependency order
    try:
        # Get all tables
        db_cursor.execute("SHOW TABLES")
        tables = [row[0] for row in db_cursor.fetchall()]
        
        # Temporarily disable foreign key checks for cleanup
        db_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Cleanup order (reverse of creation order)
        cleanup_order = [
            'tbl_shareTransaction', 'tbl_shareHistory', 'tbl_share',
            'tbl_accountingEntry', 'tbl_transaction', 'tbl_planningEntry',
            'tbl_planning', 'tbl_category', 'tbl_accountReserve',
            'tbl_accountImportPath', 'tbl_accountImportFormat',
            'tbl_loan', 'tbl_account'
        ]
        
        for table in cleanup_order:
            if table in tables:
                try:
                    db_cursor.execute(f"DELETE FROM {table}")
                except Exception as e:
                    logger.warning(f"Could not cleanup {table}: {e}")
        
        # Re-enable foreign key checks
        db_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        db_connection.commit()
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")
        db_connection.rollback()


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope='function')
def api_client(test_config, current_test_user) -> requests.Session:
    """
    HTTP client for API testing with JWT authentication.
    
    Note: Requires API server to be running on localhost:8000.
    Start with: python src/main.py
    """
    import time
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
    })
    session.timeout = test_config['api_timeout']
    
    # Login and get JWT token with retry logic
    login_url = f"{test_config['api_base_url']}/api/auth/login"
    login_data = {
        "username": current_test_user.username,
        "password": current_test_user.password
    }
    
    max_retries = 3
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            response = session.post(login_url, json=login_data)
            
            if response.status_code == 500:
                # Server error - might be starting up, retry
                if attempt < max_retries - 1:
                    logger.warning(f"Login failed with 500 error, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                    
            if response.status_code != 200:
                error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type', '').startswith('application/json') else response.text
                logger.error(f"✗ Login failed (HTTP {response.status_code}): {error_detail}")
                logger.error(f"   Attempted user: {current_test_user.username}")
                response.raise_for_status()
            
            token = response.json()['token']
            
            # Set Authorization header for all subsequent requests
            session.headers.update({
                'Authorization': f'Bearer {token}'
            })
            
            logger.info(f"✓ API client authenticated for user: {current_test_user.username}")
            break
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection failed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                continue
            logger.error(f"✗ Failed to connect to API server: {e}")
            raise
        except Exception as e:
            if attempt < max_retries - 1 and "500" in str(e):
                logger.warning(f"Request failed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                continue
            logger.error(f"✗ Failed to authenticate test user: {e}")
            raise
    
    yield session
    session.close()


# ============================================================================
# ASYNC FIXTURES
# ============================================================================

@pytest.fixture(scope='session')
def event_loop():
    """Provide event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

class AssertionHelpers:
    """Helper functions for test assertions."""
    
    @staticmethod
    def assert_api_status(response: requests.Response, expected_code: int) -> None:
        """Assert API response status code."""
        assert response.status_code == expected_code, \
            f"Expected {expected_code}, got {response.status_code}: {response.text}"
    
    @staticmethod
    def assert_api_json(response: requests.Response) -> Dict[str, Any]:
        """Assert response is valid JSON and return parsed data."""
        try:
            return response.json()
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}\nResponse: {response.text}")
    
    @staticmethod
    def assert_db_record_exists(cursor, table: str, **kwargs) -> None:
        """Assert a record exists in database."""
        where_clause = ' AND '.join([f"{k}=%s" for k in kwargs.keys()])
        query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        cursor.execute(query, tuple(kwargs.values()))
        count = cursor.fetchone()[0]
        assert count > 0, f"No records found in {table} with {kwargs}"
    
    @staticmethod
    def assert_api_response_structure(response_data: Dict, required_fields: list) -> None:
        """Assert response contains required fields."""
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"


@pytest.fixture(scope='session')
def assertions() -> AssertionHelpers:
    """Provide assertion helper functions."""
    return AssertionHelpers()


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

@pytest.fixture
def performance_timer():
    """Context manager for timing test execution."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.end_time = time.time()
        
        @property
        def elapsed_ms(self) -> float:
            if self.start_time is None or self.end_time is None:
                return 0
            return (self.end_time - self.start_time) * 1000
    
    return PerformanceTimer()


# ============================================================================
# REPORTING & LOGGING
# ============================================================================

@pytest.fixture(scope='session', autouse=True)
def setup_report_directory(test_config):
    """Create reports directory."""
    test_config['report_dir'].mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Reports directory: {test_config['report_dir']}")


class TestResultCollector:
    """Collect test results for reporting."""
    
    def __init__(self):
        self.results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
    
    def add_result(self, test_name: str, status: str, duration_ms: float, error: Optional[str] = None):
        """Add test result."""
        self.results['tests'].append({
            'name': test_name,
            'status': status,
            'duration_ms': duration_ms,
            'error': error
        })


@pytest.fixture(scope='session')
def test_result_collector() -> TestResultCollector:
    """Provide test result collector."""
    return TestResultCollector()


# ============================================================================
# PYTEST HOOKS FOR SMART ERROR HANDLING
# ============================================================================

class DependencyTracker:
    """Track test dependencies for smart error handling."""
    
    def __init__(self):
        self.failed_tests = set()
        self.dependent_tests = {
            'test_account_api_post': ['test_category_api_post', 'test_transaction_api_post'],
            'test_category_api_post': ['test_transaction_api_post'],
            'test_transaction_api_post': ['test_year_overview_api_get'],
            'test_sharing_api_post': ['test_year_overview_api_get'],
        }
    
    def should_skip(self, test_name: str) -> bool:
        """Check if test should be skipped due to dependency failure."""
        for dependent, tests in self.dependent_tests.items():
            if test_name in tests and dependent in self.failed_tests:
                return True
        return False


dependency_tracker = DependencyTracker()


@pytest.fixture(scope='session')
def dependency_tracker_fixture():
    """Provide dependency tracker."""
    return dependency_tracker


def pytest_runtest_makereport(item, call):
    """Hook to track failed tests."""
    if call.when == "call":
        if call.excinfo is not None:
            dependency_tracker.failed_tests.add(item.name)


def pytest_runtest_setup(item):
    """Skip tests if dependencies failed."""
    if dependency_tracker.should_skip(item.name):
        pytest.skip(f"Dependency failed for {item.name}")


# ============================================================================
# FACTORY & FAKER FIXTURES (Task 2.2 & 2.3)
# ============================================================================

@pytest.fixture(scope='session')
def test_data_generator():
    """Provide Faker-based test data generator."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from fake_data import TestDataGenerator
    return TestDataGenerator(locale='de_DE')


@pytest.fixture(scope='function')
def account_factory(db_cursor, db_connection):
    """Provide account factory for test data creation."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from factories import AccountFactory
    
    class AccountFactoryInterface:
        created_ids = []
        
        def create(self, **kwargs) -> int:
            """Create and insert account into database."""
            account = AccountFactory.build(**kwargs)
            account_id = AccountFactory.insert_into_db(db_cursor, account)
            self.created_ids.append(account_id)
            db_connection.commit()
            return account_id
        
        def create_batch(self, count=5, **kwargs) -> list:
            """Create multiple accounts with unique names."""
            ids = []
            import time
            timestamp = int(time.time() * 1000)  # Use timestamp for uniqueness
            for i in range(count):
                # Override name to ensure uniqueness
                batch_kwargs = kwargs.copy()
                if 'name' not in batch_kwargs:
                    batch_kwargs['name'] = f"Account_{timestamp}_{i}"
                ids.append(self.create(**batch_kwargs))
            return ids
    
    factory = AccountFactoryInterface()
    yield factory
    # Cleanup handled by cleanup_test_data fixture


@pytest.fixture(scope='function')
def category_factory(db_cursor, db_connection):
    """Provide category factory for test data creation."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from factories import CategoryFactory
    
    class CategoryFactoryInterface:
        created_ids = []
        
        def create(self, **kwargs) -> int:
            """Create and insert category into database."""
            category = CategoryFactory.build(**kwargs)
            category_id = CategoryFactory.insert_into_db(db_cursor, category)
            self.created_ids.append(category_id)
            db_connection.commit()
            return category_id
        
        def create_batch(self, count=5, **kwargs) -> list:
            """Create multiple categories with unique names."""
            ids = []
            import time
            timestamp = int(time.time() * 1000)  # Use timestamp for uniqueness
            for i in range(count):
                # Override name to ensure uniqueness
                batch_kwargs = kwargs.copy()
                if 'name' not in batch_kwargs:
                    batch_kwargs['name'] = f"Category_{timestamp}_{i}"
                ids.append(self.create(**batch_kwargs))
            return ids
    
    factory = CategoryFactoryInterface()
    yield factory


@pytest.fixture(scope='function')
def transaction_factory(db_cursor, db_connection):
    """Provide transaction factory for test data creation."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from factories import TransactionFactory
    
    class TransactionFactoryInterface:
        created_ids = []
        
        def create(self, account_id, **kwargs) -> int:
            """Create and insert transaction into database."""
            transaction = TransactionFactory.build(account=account_id, **kwargs)
            transaction_id = TransactionFactory.insert_into_db(db_cursor, transaction)
            self.created_ids.append(transaction_id)
            db_connection.commit()
            return transaction_id
        
        def create_batch(self, account_id, count=5, **kwargs) -> list:
            """Create multiple transactions."""
            ids = []
            for _ in range(count):
                ids.append(self.create(account_id, **kwargs))
            return ids
    
    factory = TransactionFactoryInterface()
    yield factory


@pytest.fixture(scope='function')
def planning_factory(db_cursor, db_connection):
    """Provide planning factory for test data creation."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from factories import PlanningFactory
    
    class PlanningFactoryInterface:
        created_ids = []
        
        def create(self, account_id, category_id, **kwargs) -> int:
            """Create and insert planning into database."""
            planning = PlanningFactory.build(account=account_id, category=category_id, **kwargs)
            planning_id = PlanningFactory.insert_into_db(db_cursor, planning)
            self.created_ids.append(planning_id)
            db_connection.commit()
            return planning_id
        
        def create_batch(self, account_id, category_ids, count=5, **kwargs) -> list:
            """Create multiple planning entries."""
            import random
            ids = []
            for _ in range(count):
                cat_id = random.choice(category_ids)
                ids.append(self.create(account_id, cat_id, **kwargs))
            return ids
    
    factory = PlanningFactoryInterface()
    yield factory


@pytest.fixture(scope='function')
def share_factory(db_cursor, db_connection):
    """Provide share factory for test data creation."""
    sys.path.insert(0, str(Path(__file__).parent / 'data'))
    from factories import ShareFactory
    
    class ShareFactoryInterface:
        created_ids = []
        
        def create(self, **kwargs) -> int:
            """Create and insert share into database."""
            share = ShareFactory.build(**kwargs)
            share_id = ShareFactory.insert_into_db(db_cursor, share)
            self.created_ids.append(share_id)
            db_connection.commit()
            return share_id
        
        def create_batch(self, count=5, **kwargs) -> list:
            """Create multiple shares."""
            ids = []
            for _ in range(count):
                ids.append(self.create(**kwargs))
            return ids
    
    factory = ShareFactoryInterface()
    yield factory


@pytest.fixture(scope='function')
def test_data_bundle(account_factory, category_factory, transaction_factory, 
                     planning_factory, share_factory, test_data_generator):
    """Provide a bundle of factories for convenient test data creation."""
    class TestDataBundle:
        def __init__(self):
            self.accounts = account_factory
            self.categories = category_factory
            self.transactions = transaction_factory
            self.planning = planning_factory
            self.shares = share_factory
            self.faker = test_data_generator
        
        def create_full_test_scenario(self, num_accounts=2, categories_per_account=5):
            """Create a complete test scenario with accounts, categories, transactions."""
            accounts = self.accounts.create_batch(count=num_accounts)
            categories = self.categories.create_batch(count=categories_per_account)
            
            transactions = []
            for account_id in accounts:
                trans_ids = self.transactions.create_batch(account_id, count=10)
                transactions.extend(trans_ids)
            
            return {
                'accounts': accounts,
                'categories': categories,
                'transactions': transactions
            }
    
    return TestDataBundle()


# ============================================================================
# INITIALIZATION & LOGGING
# ============================================================================

def pytest_configure(config):
    """Configure pytest."""
    logger.info("=" * 70)
    logger.info("FiniA Test Suite - Issue #32: Implementing a test bench")
    logger.info("=" * 70)
    logger.info(f"Test User: {DEFAULT_TEST_USER}")
    logger.info(f"Environment: {os.getenv('FINIA_ENV', 'test')}")
    logger.info(f"Test Mode: {os.getenv('TEST_MODE', 'true')}")


def pytest_collection_finish(session):
    """Log test collection results."""
    logger.info(f"✓ Collected {session.config.hook.pytest_collection_modifyitems.get_hookimpls()} tests")


# ============================================================================
# SESSION SETUP & CLEANUP
# ============================================================================

def _reset_test_database(connection, db_name: str):
    """
    Completely reset the test database by dropping all objects.
    
    This ensures a clean slate for migrations, even after aborted tests.
    Drops: Views, Tables, Triggers, Procedures, Functions, Events
    
    Args:
        connection: Active MySQL connection
        db_name: Name of the database to reset
    """
    cursor = connection.cursor()
    try:
        logger.info("=" * 70)
        logger.info(f"RESETTING DATABASE: {db_name}")
        logger.info("=" * 70)
        
        # Disable foreign key checks to allow dropping in any order
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 1. Drop all VIEWS first (they might reference tables)
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        views = cursor.fetchall()
        if views:
            logger.info(f"Dropping {len(views)} view(s)...")
            for (view_name, _) in views:
                cursor.execute(f"DROP VIEW IF EXISTS `{view_name}`")
                logger.debug(f"  ✓ Dropped view: {view_name}")
        
        # 2. Drop all TRIGGERS
        cursor.execute("SHOW TRIGGERS")
        triggers = cursor.fetchall()
        if triggers:
            logger.info(f"Dropping {len(triggers)} trigger(s)...")
            for trigger_row in triggers:
                trigger_name = trigger_row[0]  # Trigger name is first column
                cursor.execute(f"DROP TRIGGER IF EXISTS `{trigger_name}`")
                logger.debug(f"  ✓ Dropped trigger: {trigger_name}")
        
        # 3. Drop all PROCEDURES
        cursor.execute(f"SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE' AND ROUTINE_SCHEMA = '{db_name}'")
        procedures = cursor.fetchall()
        if procedures:
            logger.info(f"Dropping {len(procedures)} procedure(s)...")
            for (proc_name,) in procedures:
                cursor.execute(f"DROP PROCEDURE IF EXISTS `{proc_name}`")
                logger.debug(f"  ✓ Dropped procedure: {proc_name}")
        
        # 4. Drop all FUNCTIONS
        cursor.execute(f"SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION' AND ROUTINE_SCHEMA = '{db_name}'")
        functions = cursor.fetchall()
        if functions:
            logger.info(f"Dropping {len(functions)} function(s)...")
            for (func_name,) in functions:
                cursor.execute(f"DROP FUNCTION IF EXISTS `{func_name}`")
                logger.debug(f"  ✓ Dropped function: {func_name}")
        
        # 5. Drop all EVENTS
        cursor.execute(f"SELECT EVENT_NAME FROM INFORMATION_SCHEMA.EVENTS WHERE EVENT_SCHEMA = '{db_name}'")
        events = cursor.fetchall()
        if events:
            logger.info(f"Dropping {len(events)} event(s)...")
            for (event_name,) in events:
                cursor.execute(f"DROP EVENT IF EXISTS `{event_name}`")
                logger.debug(f"  ✓ Dropped event: {event_name}")
        
        # 6. Drop all TABLES (BASE TABLE type)
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tables = cursor.fetchall()
        if tables:
            logger.info(f"Dropping {len(tables)} table(s)...")
            for (table_name, _) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                logger.debug(f"  ✓ Dropped table: {table_name}")
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # Commit all drops
        connection.commit()
        
        # Verify database is empty
        cursor.execute("SHOW FULL TABLES")
        remaining = cursor.fetchall()
        if remaining:
            logger.warning(f"⚠ {len(remaining)} object(s) still remain in database!")
            for obj in remaining:
                logger.warning(f"  - {obj}")
        else:
            logger.info("✓ Database is completely empty and ready for migration")
        
        logger.info("=" * 70)
    except Exception as e:
        logger.error(f"✗ Error during database reset: {e}")
        raise
    finally:
        cursor.close()


@pytest.fixture(scope="session", autouse=True)
def init_test_database(test_config):
    """Initialize test database with migrations (one-time setup)."""
    import mysql.connector
    
    logger.info(f"\n{'='*70}")
    logger.info("PHASE 1: TEST DATABASE INITIALIZATION")
    logger.info(f"{'='*70}")
    logger.info(f"Database: {test_config['db_name']}")
    logger.info(f"Host: {test_config['db_host']}:{test_config['db_port']}")
    
    # Use dedicated connection for initialization
    init_conn = None
    try:
        init_conn = mysql.connector.connect(
            host=test_config['db_host'],
            port=test_config['db_port'],
            user=test_config['db_user'],
            password=test_config['db_password'],
            database=test_config['db_name']
        )
        
        # ALWAYS reset database at the beginning to ensure clean state
        _reset_test_database(init_conn, test_config['db_name'])
        
        # Import migration runner
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from migration_runner import MigrationRunner
        
        migrations_dir = Path(__file__).parent.parent / 'db' / 'migrations'
        runner = MigrationRunner(
            {
                'host': test_config['db_host'],
                'port': test_config['db_port'],
                'user': test_config['db_user'],
                'password': test_config['db_password'],
                'database': test_config['db_name']
            },
            str(migrations_dir)
        )
        
        result = runner.run_migrations(dry_run=False)
        
        # Migration runner returns: {'applied': [...], 'skipped': [...], 'total_time_ms': int}
        logger.info(f"✓ Database initialized successfully")
        logger.info(f"  Applied migrations: {len(result['applied'])}")
        logger.info(f"  Skipped migrations: {len(result['skipped'])}")
        logger.info(f"  Total time: {result['total_time_ms']}ms")
    
    except Exception as e:
        logger.error(f"✗ Test database initialization failed: {e}")
        raise
    finally:
        if init_conn and init_conn.is_connected():
            init_conn.close()

    yield
    
    # CLEANUP: Reset database after all tests
    logger.info(f"\n{'='*70}")
    logger.info("TEST SESSION CLEANUP")
    logger.info(f"{'='*70}")
    
    cleanup_conn = None
    try:
        cleanup_conn = mysql.connector.connect(
            host=test_config['db_host'],
            port=test_config['db_port'],
            user=test_config['db_user'],
            password=test_config['db_password'],
            database=test_config['db_name']
        )
        
        # Reset database after tests to ensure clean state for next run
        logger.info("Cleaning up: Resetting test database...")
        _reset_test_database(cleanup_conn, test_config['db_name'])
        logger.info("✓ Test database cleanup completed")
        
    except Exception as e:
        logger.error(f"✗ Test database cleanup failed: {e}")
        # Don't raise - cleanup errors shouldn't fail the test session
    finally:
        if cleanup_conn and cleanup_conn.is_connected():
            cleanup_conn.close()
    
    logger.info("=" * 70)
