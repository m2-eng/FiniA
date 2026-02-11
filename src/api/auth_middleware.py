"""
Authentication middleware und dependencies.
"""

from fastapi import Header, HTTPException, status
import jwt
from typing import Optional

from auth.session_store import SessionNotFoundError, SessionExpiredError


# Globale Referenzen (werden beim App-Start gesetzt)
_session_store = None # finding: The information is also defined in the auth router, maybe it can be moved to a single location to avoid confusion.
_pool_manager = None # finding: The information is also defined in the auth router, maybe it can be moved to a single location to avoid confusion.
_config = None # finding: The configuration is loaded into 'config', use single source of truth to avoid confusion.


def set_auth_globals(session_store, pool_manager, config):
    """Setzt globale Auth-Referenzen."""
    global _session_store, _pool_manager, _config
    _session_store = session_store
    _pool_manager = pool_manager
    _config = config


async def get_current_session(authorization: Optional[str] = Header(None, alias="Authorization")) -> str:
    """
    Dependency: Extrahiert Session-ID aus JWT-Token.
    
    Returns:
        Session-ID
        
    Raises:
        HTTPException: Bei ungültigem/fehlendem Token oder abgelaufener Session
    """
    if not authorization:
        print("AUTH 401: No authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Keine Authentifizierung vorhanden. Bitte einloggen.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not _config or not _session_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service nicht verfügbar"
        )
    
    try:
        # "Bearer <token>" → <token>
        token = authorization.replace("Bearer ", "").strip()
        
        auth_config = _config.get('auth', {})
        payload = jwt.decode(
            token,
            auth_config.get('jwt_secret'),
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        
        if not session_id:
            print("AUTH 401: No session_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Token"
            )
        
        # Session-Aktivität aktualisieren
        _session_store.update_activity(session_id)
        
        return session_id
        
    except jwt.ExpiredSignatureError:
        print("AUTH 401: JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token abgelaufen. Bitte neu einloggen."
        )
    except jwt.InvalidTokenError:
        print("AUTH 401: Invalid JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token"
        )
    except SessionNotFoundError:
        print("AUTH 401: Session not found (möglicherweise durch Cleanup gelöscht)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session nicht gefunden. Bitte neu einloggen."
        )
    except SessionExpiredError:
        print("AUTH 401: Session expired (inactivity timeout)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session abgelaufen. Bitte neu einloggen."
        )


def get_session_store():
    """Gibt Session Store zurück."""
    return _session_store


def get_pool_manager():
    """Gibt Pool Manager zurück."""
    return _pool_manager
