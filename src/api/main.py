"""
FastAPI Main Application for FiniA Web API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routers import transactions, theme, categories, years, year_overview, accounts, category_automation, planning, shares, settings, auth, docs
from api.dependencies import get_database_config, set_auth_managers
from api.auth_middleware import set_auth_globals
from auth.session_store import SessionStore
from auth.connection_pool_manager import ConnectionPoolManager
from auth.rate_limiter import LoginRateLimiter
from cryptography.fernet import Fernet
import yaml
import asyncio
import secrets
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(
    title="FiniA API",
    description="REST API for FiniA Financial Management System",
    version=(Path(__file__).parent.parent.parent / "VERSION").read_text().strip(),
    docs_url="/api/docs",
    redoc_url="/api/redoc"
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
app.include_router(years.router, prefix="/api")
app.include_router(year_overview.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(category_automation.router, prefix="/api")
app.include_router(planning.router, prefix="/api")
app.include_router(shares.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(docs.router, prefix="/api")

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


@app.on_event("startup") # finding: 'on_event' is deprecated, use 'lifespan' event handler instead.
async def startup_event():
    """Initialize database connection and auth modules on startup"""
    # Load config for auth
    config_path = Path(__file__).parent.parent.parent / "cfg" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # MEMORY-ONLY: Generate fresh keys on every start (never stored on disk!)
    encryption_key = Fernet.generate_key().decode()
    jwt_secret = secrets.token_urlsafe(32)
    
    print("--- FiniA ", (Path(__file__).parent.parent.parent / "VERSION").read_text().strip(), " ---")
    print("✓ Auth keys generated in memory (never stored on disk)")
    print("⚠ All sessions will be invalidated on restart (by design)")
    
    # Initialize auth modules
    auth_config = config.get('auth', {}) # findig: maybe move loading 'auth_config' to the section of 'config' loading. Maybe it prevents confusion.
    session_store = SessionStore(
        encryption_key=encryption_key,
        timeout_seconds=auth_config.get('session_timeout_seconds', 3600)
    )
    
    # Get database config (single source of truth)
    db_config = get_database_config() # finding: The configuration is loaded into 'config', use single source of truth to avoid confusion.
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
    
    # Set auth managers in dependencies and auth router
    # finding: two functions using the same name 'set_auth_managers' is confusing, maybe rename one of them to clarify their purpose.
    #          This function seems to be a duplicate and can be removed in favor of the one in the auth router.
    set_auth_managers(session_store, pool_manager, rate_limiter)

    
    # Update config with loaded secrets for auth router
    auth_config_with_secrets = {**config}
    auth_config_with_secrets['auth']['jwt_secret'] = jwt_secret
    auth.set_auth_managers(session_store, pool_manager, rate_limiter, auth_config_with_secrets)
    # Set auth globals in middleware (für get_current_session dependency)
    set_auth_globals(session_store, pool_manager, auth_config_with_secrets)
    
    # finding: Log design (.e.g indentation) and wording can be improved; maybe also add additional information to the log (e.g. docker module log shall show the 'INFO' messages)
    print("✓ Auth modules initialized")
    print("✓ Database config read from cfg/config.yaml")
    print("✓ All connections use Memory-Only session-based authentication")
    
    # Start background session cleanup task
    asyncio.create_task(session_cleanup_task(session_store))


async def session_cleanup_task(session_store: SessionStore):
    """Background task to clean up expired sessions"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        cleaned = session_store.cleanup_expired_sessions()
        if cleaned > 0:
            print(f"✓ Cleaned up {cleaned} expired session(s)")


@app.on_event("shutdown") # finding: 'on_event' is deprecated, use 'lifespan' event handler instead.
async def shutdown_event(): # finding: Not sure whether everything is closed, what should be closed and what not. Review the content again.
    """Close database connection and cleanup auth resources on shutdown"""
    # Cleanup connection pools
    from api.dependencies import _pool_manager
    if _pool_manager:
        for session_id in list(_pool_manager._pools.keys()):
            _pool_manager.close_pool(session_id)
        print("✓ All connection pools closed")
    
    # Close legacy database
    from api.dependencies import get_database
    try:
        db = get_database()  #finding: The configuration is loaded into 'config', use single source of truth to avoid confusion.
        db.close()
        print("✓ Database connection closed")
    except:
        pass


    
