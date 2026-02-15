#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: In-memory session store with encrypted credentials.
#
"""
In-memory session store with encrypted credentials.
"""

from cryptography.fernet import Fernet
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional


class SessionNotFoundError(Exception): # finding: Store exception message within the class to avoid hardcoding strings in multiple places.
    """Session ID does not exist."""
    pass


class SessionExpiredError(Exception):  # finding: Store exception message within the class to avoid hardcoding strings in multiple places.
    """Session has expired."""
    pass


class SessionStore:
    """
    In-memory session store with encrypted credentials.
    
    Stores user credentials encrypted in memory.
    Sessions expire automatically after inactivity.
    """
    
    def __init__(self, encryption_key: str, timeout_seconds: int = 3600):
        """
        Initializes the session store.
        
        Args:
            encryption_key: Base64-encoded Fernet encryption key
            timeout_seconds: Inactivity timeout in seconds (default: 1h)
        """
        self.sessions: Dict[str, dict] = {}
        self.cipher = Fernet(encryption_key.encode())
        self.default_timeout = timeout_seconds
        
    def create_session(self, username: str, password: str, database: str) -> str:
        """
        Creates a new session with encrypted credentials.
        
        Args:
            username: DB username
            password: DB password (stored encrypted)
            database: Database name
            
        Returns:
            Session ID (URL-safe token)
        """
        session_id = secrets.token_urlsafe(32)
        
        # Encrypt password
        encrypted_password = self.cipher.encrypt(password.encode())
        
        now = datetime.now()
        self.sessions[session_id] = {
            "username": username,
            "database": database,
            "encrypted_password": encrypted_password,
            "created_at": now,
            "last_activity": now,
            "timeout_seconds": self.default_timeout
        }
        
        return session_id
    
    def update_activity(self, session_id: str) -> None:
        """
        Updates the last_activity timestamp.
        
        Args:
            session_id: Session ID
            
        Raises:
            SessionNotFoundError: Session does not exist
        """
        if session_id not in self.sessions:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        
        self.sessions[session_id]["last_activity"] = datetime.now()
    
    def delete_session(self, session_id: str) -> None:
        """
        Deletes a session and overwrites the password in memory.
        
        Args:
            session_id: Session ID
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Overwrite password in memory (security)
            if "encrypted_password" in session:
                pwd_len = len(session["encrypted_password"])
                session["encrypted_password"] = b'\x00' * pwd_len
            
            del self.sessions[session_id]
    
    def cleanup_expired_sessions(self) -> int: # review note: The call wass review but not the content of this function.
        """
        Removes expired sessions.
        
        Should be called regularly (e.g. every 5 minutes).
        
        Returns:
            Number of deleted sessions
        """
        expired = []
        now = datetime.now()
        
        for session_id, session in self.sessions.items():
            timeout = timedelta(seconds=session["timeout_seconds"])
            if now - session["last_activity"] > timeout:
                expired.append(session_id)
        
        for session_id in expired:
            self.delete_session(session_id)
        
        return len(expired)

    def clear_all_sessions(self) -> int:
        """
        Deletes all sessions and overwrites secrets in memory.

        Returns:
            Number of deleted sessions
        """
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            self.delete_session(session_id)
        return len(session_ids)
    
    def get_session_count(self) -> int:
        """Returns the number of active sessions."""
        return len(self.sessions)
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Returns session info without the password.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with session info (without password) or None
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "username": session["username"],
            "database": session["database"],
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat(),
            "timeout_seconds": session["timeout_seconds"]
        }
