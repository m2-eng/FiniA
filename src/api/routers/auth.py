#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Authentication API Router - login and session management.
#
"""
Authentication API Router - login and session management.
"""

from fastapi import APIRouter, HTTPException, Response, Depends, status, Header
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from mysql.connector import Error

from auth.session_store import SessionNotFoundError, SessionExpiredError
from auth.utils import get_database_name
from api.error_handling import handle_db_errors
from api.auth_context import AuthContext, get_auth_context


router = APIRouter(prefix="/auth", tags=["authentication"])


def get_session_from_token(
    authorization: str = Header(None),
    auth_context: AuthContext = Depends(get_auth_context),
) -> str:
    """
    Dependency: Extracts session ID from JWT token.
    
    Raises:
        HTTPException: On invalid/missing token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # "Bearer <token>" -> <token>
        token = authorization.replace("Bearer ", "")
        
        auth_config = auth_context.config.get('auth', {})
        payload = jwt.decode(
            token,
            auth_config.get('jwt_secret'),
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )
        
        # Update session activity
        auth_context.session_store.update_activity(session_id)
        
        return session_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token."
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found."
        )
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired."
        )


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    token: str
    username: str
    database: str
    expires_in: int


@router.post("/login", response_model=LoginResponse)
@handle_db_errors("user login")
async def login(
    credentials: LoginRequest,
    response: Response,
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    User login with MySQL credentials.
    
    Authenticates the user directly via MySQL and creates a session.
    """
    username = credentials.username.strip()
    password = credentials.password
    
    # Check rate limiting
    if not auth_context.rate_limiter.is_allowed(username):
        retry_after = auth_context.rate_limiter.get_retry_after(username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please wait {retry_after} seconds and try again.",
            headers={"Retry-After": str(retry_after)}
        )
    
    # Derive database name
    try:
        auth_config = auth_context.config.get('auth', {})
        database_name = get_database_name(
            username,
            username_prefix=auth_config.get('username_prefix', 'finia_'),
            database_prefix=auth_config.get('database_prefix', 'finiaDB_')
        )
    except ValueError as e:
        auth_context.rate_limiter.record_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Attempt MySQL authentication
    try:
        import mysql.connector
        
        db_config = auth_context.config.get('database', {})
        test_conn = mysql.connector.connect(
            host=db_config.get('host'),
            port=db_config.get('port', 3306),
            user=username,
            password=password,
            database=database_name,
            connect_timeout=5
        )
        test_conn.close()
        
    except Error as e:
        # Login failed
        auth_context.rate_limiter.record_attempt(username)
        
        remaining = auth_context.rate_limiter.get_remaining_attempts(username)
        detail = "Invalid credentials."
        
        if remaining > 0:
            detail += f" ({remaining} attempts remaining)"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )
    
    # Login successful - create session
    try:
        session_id = auth_context.session_store.create_session(username, password, database_name)
        
        # Create connection pool
        auth_context.pool_manager.create_pool(session_id, username, password, database_name)
        
        # Reset rate limiter
        auth_context.rate_limiter.reset(username)
        
        # Create JWT token
        auth_config = auth_context.config.get('auth', {})
        expiry_hours = auth_config.get('jwt_expiry_hours', 24)
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        token_payload = {
            "session_id": session_id,
            "username": username,
            "database": database_name,
            "exp": expires_at
        }
        
        token = jwt.encode(
            token_payload,
            auth_config.get('jwt_secret'),
            algorithm="HS256"
        )
        
        # Set cookie (HttpOnly, Secure)
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=False,  # TODO: True in Production mit HTTPS
            samesite="strict",
            max_age=expiry_hours * 3600
        )
        
        return LoginResponse(
            token=token,
            username=username,
            database=database_name,
            expires_in=expiry_hours * 3600
        )
        
    except Exception as e:
        # Cleanup on error
        if session_id:
            auth_context.session_store.delete_session(session_id)
            auth_context.pool_manager.close_pool(session_id)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.post("/logout")
async def logout(
    response: Response,
    session_id: str = Depends(get_session_from_token),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    User logout - deletes the session and connection pool.
    """
    # Delete session
    auth_context.session_store.delete_session(session_id)
    auth_context.pool_manager.close_pool(session_id)
    
    # Delete cookie
    response.delete_cookie(key="auth_token")
    
    return {"message": "Signed out successfully"}


@router.get("/session")
async def get_session_info(
    session_id: str = Depends(get_session_from_token),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    Returns session info (without password).
    """
    info = auth_context.session_store.get_session_info(session_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    
    return info


# All imports are already handled at the top
