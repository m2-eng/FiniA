"""
Script to update all API routers to use auth-based DB connections
"""
import os
import re
from pathlib import Path

# Base path
base_path = Path(__file__).parent
routers_path = base_path / "src" / "api" / "routers"

# Files to update
files_to_update = [
    "transactions.py",
    "year_overview.py",
    "category_automation.py",
    "settings.py",
    "shares.py",
    "planning.py",
    "accounts.py",
    "categories.py",
]

def update_file(filepath):
    """Update a single file to use auth-based connections"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace imports
    content = re.sub(
        r'from api\.dependencies import get_db_cursor\b',
        'from api.dependencies import get_db_cursor_with_auth as get_db_cursor',
        content
    )
    
    content = re.sub(
        r'from api\.dependencies import get_db_connection\b',
        'from api.dependencies import get_db_connection_with_auth as get_db_connection',
        content
    )
    
    # Handle multi-line imports like: from api.dependencies import get_db_cursor, get_db_connection
    content = re.sub(
        r'from api\.dependencies import ([^;\n]*?)get_db_cursor([^;\n]*?)get_db_connection([^;\n]*?)\n',
        r'from api.dependencies import \1get_db_cursor_with_auth as get_db_cursor\2get_db_connection_with_auth as get_db_connection\3\n',
        content
    )
    
    content = re.sub(
        r'from api\.dependencies import ([^;\n]*?)get_db_connection([^;\n]*?)get_db_cursor([^;\n]*?)\n',
        r'from api.dependencies import \1get_db_connection_with_auth as get_db_connection\2get_db_cursor_with_auth as get_db_cursor\3\n',
        content
    )
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Updated: {filepath.name}")
        return True
    else:
        print(f"- No changes: {filepath.name}")
        return False

# Update all files
updated_count = 0
for filename in files_to_update:
    filepath = routers_path / filename
    if filepath.exists():
        if update_file(filepath):
            updated_count += 1
    else:
        print(f"⚠ Not found: {filename}")

print(f"\n✓ Updated {updated_count} files")
