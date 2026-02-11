"""
Authentication API Router - Login und Session-Management.
"""

from fastapi import APIRouter, HTTPException, Response, Depends, status, Header
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta
from mysql.connector import Error

from auth.session_store import SessionStore, SessionNotFoundError, SessionExpiredError
from auth.connection_pool_manager import ConnectionPoolManager, PoolNotFoundError
from auth.rate_limiter import LoginRateLimiter
from auth.utils import get_database_name
from api.error_handling import handle_db_errors


router = APIRouter(prefix="/auth", tags=["authentication"])


# Globale Instanzen (werden beim App-Start initialisiert)
session_store: Optional[SessionStore] = None
pool_manager: Optional[ConnectionPoolManager] = None
rate_limiter: Optional[LoginRateLimiter] = None
config: Optional[dict] = None


def get_session_from_token(authorization: str = Header(None)) -> str:
    """
    Dependency: Extrahiert Session-ID aus JWT-Token.
    
    Raises:
        HTTPException: Bei ungültigem/fehlendem Token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Keine Authentifizierung vorhanden",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # "Bearer <token>" → <token>
        token = authorization.replace("Bearer ", "")
        
        auth_config = config.get('auth', {})
        payload = jwt.decode(
            token,
            auth_config.get('jwt_secret'),
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Token"
            )
        
        # Session-Aktivität aktualisieren
        session_store.update_activity(session_id)
        
        return session_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token abgelaufen"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session nicht gefunden"
        )
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session abgelaufen"
        )


def set_auth_managers(
    store: SessionStore,
    manager: ConnectionPoolManager,
    limiter: LoginRateLimiter,
    app_config: dict
):
    """
    Setzt die Auth-Manager-Instanzen (wird von main.py aufgerufen).
    
    Args:
        store: SessionStore Instanz
        manager: ConnectionPoolManager Instanz
        limiter: LoginRateLimiter Instanz
        app_config: Config-Dict mit auth-Sektion
    """
    global session_store, pool_manager, rate_limiter, config
    
    session_store = store
    pool_manager = manager
    rate_limiter = limiter
    config = app_config
    
    print("✓ Auth router managers set")


class LoginRequest(BaseModel):
    """Login-Request Model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login-Response Model."""
    token: str
    username: str
    database: str
    expires_in: int


@router.post("/login", response_model=LoginResponse)
@handle_db_errors("user login")
async def login(credentials: LoginRequest, response: Response):
    """
    User-Login mit MySQL-Credentials.
    
    Authentifiziert User direkt über MySQL und erstellt Session.
    """
    if not all([session_store, pool_manager, rate_limiter, config]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    
    username = credentials.username.strip()
    password = credentials.password
    
    # Rate Limiting prüfen
    if not rate_limiter.is_allowed(username):
        retry_after = rate_limiter.get_retry_after(username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zu viele Login-Versuche. Bitte warten Sie {retry_after} Sekunden.",
            headers={"Retry-After": str(retry_after)}
        )
    
    # Datenbankname ableiten
    try:
        auth_config = config.get('auth', {})
        database_name = get_database_name(
            username,
            username_prefix=auth_config.get('username_prefix', 'finia_'),
            database_prefix=auth_config.get('database_prefix', 'finiaDB_')
        )
    except ValueError as e:
        rate_limiter.record_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # MySQL-Authentifizierung versuchen
    try:
        import mysql.connector
        
        db_config = config.get('database', {})
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
        # Login fehlgeschlagen
        rate_limiter.record_attempt(username)
        
        remaining = rate_limiter.get_remaining_attempts(username)
        detail = "Ungültige Anmeldedaten"
        
        if remaining > 0:
            detail += f" ({remaining} Versuche übrig)"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )
    
    # Login erfolgreich - Session erstellen
    try:
        session_id = session_store.create_session(username, password, database_name)
        
        # Connection Pool erstellen
        pool_manager.create_pool(session_id, username, password, database_name)
        
        # Rate Limiter zurücksetzen
        rate_limiter.reset(username)
        
        # JWT-Token erstellen
        auth_config = config.get('auth', {})
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
        
        # Cookie setzen (HttpOnly, Secure)
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
        # Cleanup bei Fehler
        if session_id:
            session_store.delete_session(session_id)
            pool_manager.close_pool(session_id)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Erstellen der Session: {str(e)}"
        )


@router.post("/logout")
async def logout(response: Response, session_id: str = Depends(get_session_from_token)):
    """
    User-Logout - Löscht Session und Connection Pool.
    """
    if not all([session_store, pool_manager]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    
    # Session löschen
    session_store.delete_session(session_id)
    pool_manager.close_pool(session_id)
    
    # Cookie löschen
    response.delete_cookie(key="auth_token")
    
    return {"message": "Erfolgreich abgemeldet"}


@router.get("/session")
async def get_session_info(session_id: str = Depends(get_session_from_token)):
    """
    Gibt Session-Info zurück (ohne Passwort).
    """
    if not session_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    
    info = session_store.get_session_info(session_id)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session nicht gefunden"
        )
    
    return info


# Alle Importe am Anfang bereits erledigt
