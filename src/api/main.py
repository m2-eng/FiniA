#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: FastAPI Main Application for FiniA Web API
#
"""
FastAPI Main Application for FiniA Web API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager, suppress
import logging

from api.routers import transactions, theme, categories, year_overview, accounts, category_automation, planning, shares, settings, auth, docs, setup
from api.dependencies import get_database_config
from api.auth_context import set_auth_context
from auth.session_store import SessionStore
from auth.connection_pool_manager import ConnectionPoolManager
from auth.rate_limiter import LoginRateLimiter
from cryptography.fernet import Fernet
import asyncio
import secrets
from pathlib import Path

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event(app)
    try:
        yield
    finally:
        await shutdown_event(app)

# Initialize FastAPI app
app = FastAPI(
    title="FiniA API",
    description="REST API for FiniA Financial Management System",
    version=(Path(__file__).parent.parent.parent / "VERSION").read_text().strip(),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # finding: Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"], # finding: Adjust methods as needed
    allow_headers=["*"], # finding: Adjust headers as needed
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(theme.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(year_overview.router, prefix="/api")
app.include_router(year_overview.years_router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(category_automation.router, prefix="/api")
app.include_router(planning.router, prefix="/api")
app.include_router(shares.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(docs.router, prefix="/api")
app.include_router(setup.router, prefix="/api")

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FiniA API",
        "version": (Path(__file__).parent.parent.parent / "VERSION").read_text().strip()
    }

# Mount static files for web frontend (registered AFTER API routes + health)
web_path = Path(__file__).parent.parent / "web"
if web_path.exists():
    app.mount("/", StaticFiles(directory=str(web_path), html=True), name="web")


async def startup_event(app: FastAPI):
    """Initialize database connection and auth modules on startup"""
    # Load configuration (single source of truth)
    config = get_database_config()
    auth_config = get_database_config('auth')
    db_config = get_database_config('database')
    
    logger.info("FiniA %s", (Path(__file__).parent.parent.parent / "VERSION").read_text().strip())

    # MEMORY-ONLY: Generate fresh keys on every start (never stored on disk!)
    encryption_key = Fernet.generate_key().decode()
    jwt_secret = secrets.token_urlsafe(32)
    
    logger.info("Auth keys generated in memory (never stored on disk)")
    logger.warning("All sessions will be invalidated on restart (by design)")
    
    # Initialize auth modules
    session_store = SessionStore(
        encryption_key=encryption_key,
        timeout_seconds=auth_config.get('session_timeout_seconds', 3600)
    )
    
    # Get database config (single source of truth)
    db_host = db_config.get('host', 'localhost')
    db_port = db_config.get('port', 3306)
    
    pool_manager = ConnectionPoolManager(
        host=db_host,
        port=db_port,
        pool_size=auth_config.get('pool_size', 5)
    )
    
    rate_limiter = LoginRateLimiter(
        max_attempts=auth_config.get('max_login_attempts', 5),
        window_minutes=auth_config.get('rate_limit_window_minutes', 15)
    )
    
    # Update config with loaded secrets for auth context
    auth_config_with_secrets = {**config}
    auth_config_with_secrets['auth']['jwt_secret'] = jwt_secret
    set_auth_context(app, session_store, pool_manager, rate_limiter, auth_config_with_secrets)
    
    logger.info("Auth modules initialized")
    logger.info("Database config read from cfg/config.yaml")
    logger.info("All connections use memory-only session-based authentication")
    
    # Start background session cleanup task
    app.state.session_cleanup_task = asyncio.create_task(
        session_cleanup_task(session_store)
    )


async def session_cleanup_task(session_store: SessionStore):
    """Background task to clean up expired sessions"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        cleaned = session_store.cleanup_expired_sessions()
        if cleaned > 0:
            logger.info("Cleaned up %s expired session(s)", cleaned)


async def shutdown_event(app: FastAPI):
    """Close database connection and cleanup auth resources on shutdown"""
    # Stop background cleanup task
    cleanup_task = getattr(app.state, "session_cleanup_task", None)
    if cleanup_task:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

    # Cleanup auth secrets and connection pools
    auth_context = getattr(app.state, "auth_context", None)
    if auth_context:
        if auth_context.session_store:
            cleared = auth_context.session_store.clear_all_sessions()
            logger.info("Cleared %s session(s) from memory", cleared)

        if auth_context.config:
            auth_config = auth_context.config.get("auth", {})
            jwt_secret = auth_config.get("jwt_secret")
            if jwt_secret:
                auth_config["jwt_secret"] = "0" * len(jwt_secret)
                auth_config.pop("jwt_secret", None)

        if auth_context.pool_manager:
            closed = auth_context.pool_manager.close_all()
            logger.info("All connection pools closed (%s)", closed)

    # No legacy singleton database to close


    
