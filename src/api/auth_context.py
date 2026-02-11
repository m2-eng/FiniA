"""
Centralized auth context storage for the app.
"""

# minimal helper for shared auth state.

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthContext:
    session_store: object
    pool_manager: object
    rate_limiter: object
    config: dict


def set_auth_context(
    app,
    session_store: object,
    pool_manager: object,
    rate_limiter: object,
    config: dict,
) -> None:
    """Attach auth context to the FastAPI app state."""
    app.state.auth_context = AuthContext(
        session_store=session_store,
        pool_manager=pool_manager,
        rate_limiter=rate_limiter,
        config=config,
    )


def get_auth_context(request: Request) -> AuthContext:
    """Fetch auth context from the FastAPI app state."""
    context: Optional[AuthContext] = getattr(request.app.state, "auth_context", None)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized",
        )
    return context
