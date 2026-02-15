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
from pydantic import BaseModel, Field
from pathlib import Path
import os

from api.dependencies import get_database_config
from api.error_handling import handle_db_errors
from Database import Database
from DatabaseCreator import DatabaseCreator
from DataImporter import DataImporter


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


def _resolve_db_config(database_name_override: str | None) -> tuple[dict, str, Path, Path]:
    db_config = get_database_config("database")
    database_name = database_name_override or db_config.get("name") or "FiniA"

    sql_file = Path(db_config.get("sql_file", "./db/finia_draft.sql"))
    data_file = Path(db_config.get("init_data", "./cfg/data.yaml"))

    return db_config, database_name, sql_file, data_file


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
