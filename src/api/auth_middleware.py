"""
Authentication middleware und dependencies.
"""

# JWT session dependency using app auth context.

from fastapi import Header, HTTPException, Request, status
import jwt
from typing import Optional

from auth.session_store import SessionNotFoundError, SessionExpiredError
from api.auth_context import get_auth_context

async def get_current_session(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
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
    
    auth_context = get_auth_context(request)
    
    try:
        # "Bearer <token>" → <token>
        token = authorization.replace("Bearer ", "").strip()
        
        auth_config = auth_context.config.get('auth', {})
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
        auth_context.session_store.update_activity(session_id)
        
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
