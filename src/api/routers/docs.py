#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Documentation Router for FiniA API
#
"""
Documentation Router for FiniA API
Serves markdown documentation files as plain text
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pathlib import Path

router = APIRouter()

# Base path for documentation
DOCS_BASE_PATH = Path(__file__).parent.parent.parent.parent / "docs"


@router.get("/docs/{file_path:path}")
async def get_documentation(file_path: str):
    """
    Serve markdown documentation files
    
    Example: /api/docs/tutorials/getting_started.md
    """
    try:
        # Prevent directory traversal attacks
        if ".." in file_path or not file_path.endswith(".md"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Construct full file path
        full_path = DOCS_BASE_PATH / file_path
        
        # Verify the file exists and is within DOCS_BASE_PATH
        try:
            full_path = full_path.resolve()
            DOCS_BASE_PATH.resolve()
            if not str(full_path).startswith(str(DOCS_BASE_PATH.resolve())):
                raise HTTPException(status_code=403, detail="Access denied")
        except (RuntimeError, ValueError):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Documentation file not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="Not a file")
        
        # Read and return the file content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return PlainTextResponse(content)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading documentation: {str(e)}")
