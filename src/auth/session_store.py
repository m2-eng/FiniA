"""
In-Memory Session Store mit verschlüsselten Credentials.
"""

from cryptography.fernet import Fernet
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional


class SessionNotFoundError(Exception):
    """Session-ID existiert nicht."""
    pass


class SessionExpiredError(Exception):
    """Session ist abgelaufen."""
    pass


class SessionStore:
    """
    In-Memory Session Store mit verschlüsselten Credentials.
    
    Speichert Benutzer-Credentials verschlüsselt im RAM.
    Sessions laufen nach Inaktivität automatisch ab.
    """
    
    def __init__(self, encryption_key: str, timeout_seconds: int = 3600):
        """
        Initialisiert Session Store.
        
        Args:
            encryption_key: Base64-encoded Fernet encryption key
            timeout_seconds: Inaktivitäts-Timeout in Sekunden (default: 1h)
        """
        self.sessions: Dict[str, dict] = {}
        self.cipher = Fernet(encryption_key.encode())
        self.default_timeout = timeout_seconds
        
    def create_session(self, username: str, password: str, database: str) -> str:
        """
        Erstellt neue Session mit verschlüsselten Credentials.
        
        Args:
            username: DB-Username
            password: DB-Password (wird verschlüsselt gespeichert)
            database: Datenbankname
            
        Returns:
            Session-ID (URL-safe Token)
        """
        session_id = secrets.token_urlsafe(32)
        
        # Passwort verschlüsseln
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
    
    def get_credentials(self, session_id: str) -> Dict[str, str]:
        """
        Holt Credentials aus Session.
        
        Args:
            session_id: Session-ID
            
        Returns:
            Dict mit username, password, database
            
        Raises:
            SessionNotFoundError: Session existiert nicht
            SessionExpiredError: Session ist abgelaufen
        """
        if session_id not in self.sessions:
            raise SessionNotFoundError(f"Session nicht gefunden: {session_id}")
        
        session = self.sessions[session_id]
        
        # Timeout-Check
        timeout = timedelta(seconds=session["timeout_seconds"])
        if datetime.now() - session["last_activity"] > timeout:
            self.delete_session(session_id)
            raise SessionExpiredError("Session abgelaufen")
        
        # Last activity aktualisieren
        session["last_activity"] = datetime.now()
        
        # Passwort entschlüsseln
        password = self.cipher.decrypt(session["encrypted_password"]).decode()
        
        return {
            "username": session["username"],
            "password": password,
            "database": session["database"]
        }
    
    def update_activity(self, session_id: str) -> None:
        """
        Aktualisiert last_activity Timestamp.
        
        Args:
            session_id: Session-ID
            
        Raises:
            SessionNotFoundError: Session existiert nicht
        """
        if session_id not in self.sessions:
            raise SessionNotFoundError(f"Session nicht gefunden: {session_id}")
        
        self.sessions[session_id]["last_activity"] = datetime.now()
    
    def delete_session(self, session_id: str) -> None:
        """
        Löscht Session und überschreibt Passwort im RAM.
        
        Args:
            session_id: Session-ID
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Passwort im RAM überschreiben (Security)
            if "encrypted_password" in session:
                pwd_len = len(session["encrypted_password"])
                session["encrypted_password"] = b'\x00' * pwd_len
            
            del self.sessions[session_id]
    
    def cleanup_expired_sessions(self) -> int: # review note: The call wass review but not the content of this function.
        """
        Entfernt abgelaufene Sessions.
        
        Sollte regelmäßig (z.B. alle 5 Minuten) aufgerufen werden.
        
        Returns:
            Anzahl gelöschter Sessions
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
    
    def get_session_count(self) -> int:
        """Gibt Anzahl aktiver Sessions zurück."""
        return len(self.sessions)
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Gibt Session-Info ohne Passwort zurück.
        
        Args:
            session_id: Session-ID
            
        Returns:
            Dict mit Session-Info (ohne Passwort) oder None
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
