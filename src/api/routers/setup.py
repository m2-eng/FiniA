#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Setup API router for database creation and initialization.
#
"""
Setup API router for database creation and initialization.
"""

from fastapi import APIRouter, HTTPException, status, Header, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pathlib import Path
import os
import json
import asyncio
import threading
from queue import Queue

from api.dependencies import get_database_config
from api.error_handling import handle_db_errors
from api.auth_context import AuthContext, get_auth_context
from api.routers.auth import get_session_from_token
from auth.session_store import SessionNotFoundError
from Database import Database
from DatabaseCreator import DatabaseCreator
from DataImporter import DataImporter
from migration_runner import MigrationRunner


router = APIRouter(prefix="/setup", tags=["setup"])


class SetupDatabaseRequest(BaseModel):
    """Request model for database setup."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database_name: str | None = None


class InitDatabaseRequest(BaseModel):
    """Request model for database initialization."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database_name: str | None = None


class ApplyMigrationsRequest(BaseModel):
    """Request model for applying migrations."""
    dry_run: bool = False


def _resolve_db_config(database_name_override: str | None) -> tuple[dict, str, Path, Path]:
    db_config = get_database_config("database")
    database_name = database_name_override or db_config.get("name") or "FiniA"

    sql_file = Path(db_config.get("sql_file", "./db/finia_draft.sql"))
    data_file = Path(db_config.get("init_data", "./cfg/data.yaml"))

    return db_config, database_name, sql_file, data_file


def _get_migration_runner(session_id: str, auth_context: AuthContext) -> MigrationRunner:
    db_config = auth_context.config.get("database", {})

    try:
        session = auth_context.session_store.get_session_credentials(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found."
        ) from exc

    current = Path(__file__).resolve()
    migrations_dir = None
    for parent in [current] + list(current.parents):
        candidate = parent / "db" / "migrations"
        if candidate.is_dir():
            migrations_dir = candidate
            break

    if migrations_dir is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Migrations directory not found."
        )

    return MigrationRunner(
        db_config={
            "host": db_config.get("host", "localhost"),
            "port": db_config.get("port", 3306),
            "user": session["username"],
            "password": session["password"],
            "database": session["database"],
        },
        migrations_dir=str(migrations_dir)
    )


def _get_setup_security_config() -> dict:
    config = get_database_config()
    setup_config = config.get("setup", {}) if isinstance(config, dict) else {}
    token = os.getenv("FINIA_SETUP_TOKEN") or setup_config.get("token")
    allow_localhost = setup_config.get("allow_localhost", True)
    return {
        "token": token,
        "allow_localhost": bool(allow_localhost)
    }


def require_setup_token(
    request: Request,
    token_header: str | None = Header(None, alias="X-Setup-Token")
) -> None:
    security = _get_setup_security_config()
    required_token = security.get("token")

    if not required_token:
        return

    if security.get("allow_localhost"):
        client_ip = request.client.host if request.client else ""
        if client_ip in {"127.0.0.1", "::1"}:
            return

    if token_header != required_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing setup token."
        )


@router.post("/database", dependencies=[Depends(require_setup_token)])
@handle_db_errors("create database")
async def create_database(payload: SetupDatabaseRequest):
    """
    Create the database schema from the configured SQL dump.
    """
    db_config, database_name, sql_file, _ = _resolve_db_config(payload.database_name)

    if not sql_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SQL file not found: {sql_file}"
        )

    db = Database(
        host=db_config.get("host", "localhost"),
        user=payload.username,
        password=payload.password,
        database_name=database_name,
        port=db_config.get("port", 3306)
    )

    creator = DatabaseCreator(db)

    success = creator.create_from_file(str(sql_file))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database creation failed."
        )

    return {
        "success": True,
        "database": database_name,
        "sql_file": str(sql_file)
    }


@router.post("/init-data", dependencies=[Depends(require_setup_token)])
@handle_db_errors("initialize database")
async def init_database(payload: InitDatabaseRequest):
    """
    Initialize the database with predefined YAML data.
    """
    db_config, database_name, _, data_file = _resolve_db_config(payload.database_name)

    if not data_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data file not found: {data_file}"
        )

    db = Database(
        host=db_config.get("host", "localhost"),
        user=payload.username,
        password=payload.password,
        database_name=database_name,
        port=db_config.get("port", 3306)
    )

    importer = DataImporter(db)

    success = importer.import_data(str(data_file))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database initialization failed."
        )

    return {
        "success": True,
        "database": database_name,
        "data_file": str(data_file)
    }


@router.get("/migrations/status")
async def get_migration_status(
    session_id: str = Depends(get_session_from_token),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Return current migration status for the logged-in user database."""
    runner = _get_migration_runner(session_id, auth_context)
    return runner.get_status()


@router.post("/migrations/apply")
async def apply_migrations(
    payload: ApplyMigrationsRequest,
    session_id: str = Depends(get_session_from_token),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Apply pending migrations for the logged-in user database with real-time progress streaming."""
    
    # Create a queue for real-time progress events
    event_queue: Queue = Queue()
    result_container = {"result": None, "error": None, "version": None}
    
    def run_migration_in_thread():
        """Execute migrations in a thread and put progress events in queue."""
        try:
            runner = _get_migration_runner(session_id, auth_context)
            
            def progress_callback(phase: str, message: str, current: int, total: int):
                """Callback that puts events in queue for streaming."""
                event_queue.put({
                    "phase": phase,
                    "message": message,
                    "current": current,
                    "total": total
                })
            
            # Run migrations with progress callback
            runner.progress_callback = progress_callback
            result = runner.run_migrations(dry_run=payload.dry_run)
            result_container["result"] = result
            result_container["version"] = runner.get_current_version()
            
        except Exception as e:
            result_container["error"] = str(e)
        finally:
            # Signal completion
            event_queue.put(None)
    
    # Start migration thread
    thread = threading.Thread(target=run_migration_in_thread, daemon=True)
    thread.start()
    
    async def migration_progress_stream():
        """Stream migration progress events from the queue."""
        loop = asyncio.get_event_loop()
        
        try:
            while True:
                # Get event from queue (non-blocking in async context)
                event = await loop.run_in_executor(None, event_queue.get)
                
                if event is None:
                    # Thread finished, send final event
                    if result_container["error"]:
                        error_data = {
                            "phase": "error",
                            "message": f"Migration fehlgeschlagen: {result_container['error']}",
                            "status": "error"
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                    else:
                        completion_data = {
                            "phase": "complete",
                            "message": "Migrationen abgeschlossen",
                            "status": "success",
                            "current_version": result_container["version"],
                            "result": result_container["result"]
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
                    break
                else:
                    # Stream the progress event
                    yield f"data: {json.dumps(event)}\n\n"
                    
        except Exception as e:
            error_data = {
                "phase": "error",
                "message": f"Streaming-Fehler: {str(e)}",
                "status": "error"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        migration_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
