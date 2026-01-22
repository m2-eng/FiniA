"""
Script to update all frontend JS files to use authenticated fetch
"""
import os
import re
from pathlib import Path

# Base path
base_path = Path(__file__).parent
web_path = base_path / "src" / "web"

# Files to update
js_files = [
    "year_overview.js",
    "accounts.js",
    "accounts_management.js",
    "category_automation.js",
    "import_transactions.js",
    "shares.js",
    "settings.js",
    "planning.js",
    "table_engine.js",
]

def update_js_file(filepath):
    """Update a single JS file to use authenticated fetch"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Add requireAuth() at the start if not present
    if 'requireAuth()' not in content:
        # Find the first substantive code after comments/imports
        # Add after any initial variable declarations but before main logic
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip empty lines, comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            # Skip const/let declarations at top
            if stripped.startswith('const ') or stripped.startswith('let ') or stripped.startswith('var '):
                insert_pos = i + 1
                continue
            # Found first real code
            insert_pos = i
            break
        
        if insert_pos > 0:
            lines.insert(insert_pos, '\n// Auth-Check: User muss eingeloggt sein\nrequireAuth();\n')
            content = '\n'.join(lines)
    
    # Replace fetch with authenticatedFetch (but not for login.html)
    # Pattern: fetch('/api/...') or fetch(`/api/...`)
    content = re.sub(
        r'\bfetch\s*\(\s*(["\'])/api/',
        r'authenticatedFetch(\1/api/',
        content
    )
    
    content = re.sub(
        r'\bfetch\s*\(\s*(`)/api/',
        r'authenticatedFetch(`/api/',
        content
    )
    
    # Also handle fetch(url) where url is a variable containing /api/
    # This is trickier and might need manual review
    
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
for filename in js_files:
    filepath = web_path / filename
    if filepath.exists():
        if update_js_file(filepath):
            updated_count += 1
    else:
        print(f"⚠ Not found: {filename}")

print(f"\n✓ Updated {updated_count} frontend files")
print("\nWichtig: Bitte prüfen Sie die Dateien manuell auf:")
print("  - fetch() in Variablen (z.B. const url = ...; fetch(url))")
print("  - fetch() mit window.location oder anderen Hosts")
print("  - Event-Handler die fetch() nutzen")
