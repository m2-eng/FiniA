#!/usr/bin/env python3
"""
Replace all fetch() calls with authenticatedFetch() in JS files
"""
import re
from pathlib import Path

# Files to update
files_to_update = [
    'src/web/accounts.js',
    'src/web/planning.js',
    'src/web/shares.js',
    'src/web/import_transactions.js',
    'src/web/settings.js',
    'src/web/accounts_management.js',
    'src/web/category_automation.js'
]

def replace_fetch_calls(file_path):
    """Replace fetch( with authenticatedFetch( in a file"""
    path = Path(file_path)
    if not path.exists():
        print(f"⚠ File not found: {file_path}")
        return False
    
    content = path.read_text(encoding='utf-8')
    original = content
    
    # Replace patterns:
    # 1. await fetch(
    content = re.sub(r'await fetch\(', r'await authenticatedFetch(', content)
    
    # 2. const/let ... = fetch(
    content = re.sub(r'= fetch\(', r'= authenticatedFetch(', content)
    
    # 3. return fetch(
    content = re.sub(r'return fetch\(', r'return authenticatedFetch(', content)
    
    if content != original:
        path.write_text(content, encoding='utf-8')
        print(f"✓ Updated {file_path}")
        return True
    else:
        print(f"- No changes needed in {file_path}")
        return False

def main():
    updated_count = 0
    for file_path in files_to_update:
        if replace_fetch_calls(file_path):
            updated_count += 1
    
    print(f"\n✓ Updated {updated_count} file(s)")

if __name__ == '__main__':
    main()
