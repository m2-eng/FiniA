#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Authentication middleware and dependencies.
#
"""
Authentication middleware and dependencies.
"""

# JWT session dependency using app auth context.

import logging
from fastapi import Header, HTTPException, Request, status
import jwt
from typing import Optional

from auth.session_store import SessionNotFoundError, SessionExpiredError
from api.auth_context import get_auth_context


logger = logging.getLogger(__name__)

async def get_current_session(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Dependency: Extracts session ID from JWT token.
    
    Returns:
        Session ID
        
    Raises:
        HTTPException: On invalid/missing token or expired session
    """
    if not authorization:
        logger.warning("AUTH 401: No authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    auth_context = get_auth_context(request)
    
    try:
        # "Bearer <token>" -> <token>
        token = authorization.replace("Bearer ", "").strip()
        
        auth_config = auth_context.config.get('auth', {})
        payload = jwt.decode(
            token,
            auth_config.get('jwt_secret'),
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        
        if not session_id:
            logger.warning("AUTH 401: No session_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )
        
        # Update session activity
        auth_context.session_store.update_activity(session_id)
        
        return session_id
        
    except jwt.ExpiredSignatureError:
        logger.warning("AUTH 401: JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please sign in again."
        )
    except jwt.InvalidTokenError:
        logger.warning("AUTH 401: Invalid JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token."
        )
    except SessionNotFoundError:
        logger.warning("AUTH 401: Session not found (possibly removed by cleanup)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found. Please sign in again."
        )
    except SessionExpiredError:
        logger.warning("AUTH 401: Session expired (inactivity timeout)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again."
        )
