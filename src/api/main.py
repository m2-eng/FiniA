"""
FastAPI Main Application for FiniA Web API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routers import transactions, theme, categories, years, year_overview, accounts
from api.dependencies import set_database_instance, get_database_config, get_database_credentials
from Database import Database

# Initialize FastAPI app
app = FastAPI(
    title="FiniA API",
    description="REST API for FiniA Financial Management System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transactions.router, prefix="/api")
app.include_router(theme.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(years.router, prefix="/api")
app.include_router(year_overview.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FiniA API",
        "version": "1.0.0"
    }

# Mount static files for web frontend (registered AFTER API routes + health)
web_path = Path(__file__).parent.parent / "web"
if web_path.exists():
    app.mount("/", StaticFiles(directory=str(web_path), html=True), name="web")


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    config = get_database_config()
    credentials = get_database_credentials()
    
    # Use credentials from dependencies, with config file as fallback
    db = Database(
        host=credentials.get('host') or config.get('host', 'localhost'),
        user=credentials.get('user') or config.get('user', ''),
        password=credentials.get('password') or config.get('password', ''),
        database_name=credentials.get('name') or config.get('name', 'FiniA'),
        port=credentials.get('port') or config.get('port', 3306)
    )
    
    if not db.connect():
        raise RuntimeError("Failed to connect to database")
    
    set_database_instance(db)
    print("✓ Database connected successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    from api.dependencies import get_database
    try:
        db = get_database()
        db.close()
        print("✓ Database connection closed")
    except:
        pass


    
