"""
Rate Limiting für Login-Versuche.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List


class LoginRateLimiter:
    """
    Brute-Force-Schutz beim Login.
    
    Limitiert Login-Versuche pro Username in einem Zeitfenster.
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        """
        Initialisiert Rate Limiter.
        
        Args:
            max_attempts: Maximale Versuche im Zeitfenster
            window_minutes: Zeitfenster in Minuten
        """
        self.attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
    
    def is_allowed(self, username: str) -> bool:
        """
        Prüft ob Login-Versuch erlaubt ist.
        
        Args:
            username: DB-Username
            
        Returns:
            True wenn Login erlaubt ist
        """
        now = datetime.now()
        
        # Alte Versuche entfernen (außerhalb des Zeitfensters)
        self.attempts[username] = [
            ts for ts in self.attempts[username]
            if now - ts < self.window
        ]
        
        # Zu viele Versuche?
        if len(self.attempts[username]) >= self.max_attempts:
            return False
        
        return True
    
    def record_attempt(self, username: str) -> None:
        """
        Protokolliert Login-Versuch.
        
        Args:
            username: DB-Username
        """
        self.attempts[username].append(datetime.now())
    
    def reset(self, username: str) -> None:
        """
        Setzt Login-Versuche für Username zurück.
        
        Args:
            username: DB-Username
        """
        if username in self.attempts:
            del self.attempts[username]
    
    def get_remaining_attempts(self, username: str) -> int:
        """
        Gibt verbleibende Login-Versuche zurück.
        
        Args:
            username: DB-Username
            
        Returns:
            Anzahl verbleibender Versuche
        """
        now = datetime.now()
        
        # Aktuelle Versuche im Zeitfenster
        recent_attempts = [
            ts for ts in self.attempts.get(username, [])
            if now - ts < self.window
        ]
        
        return max(0, self.max_attempts - len(recent_attempts))
    
    def get_retry_after(self, username: str) -> int:
        """
        Gibt Sekunden bis zum nächsten erlaubten Versuch zurück.
        
        Args:
            username: DB-Username
            
        Returns:
            Sekunden bis zur Entsperrung (0 wenn erlaubt)
        """
        if self.is_allowed(username):
            return 0
        
        now = datetime.now()
        recent_attempts = [
            ts for ts in self.attempts.get(username, [])
            if now - ts < self.window
        ]
        
        if not recent_attempts:
            return 0
        
        # Ältester Versuch + Window = Entsperr-Zeitpunkt
        oldest = min(recent_attempts)
        unlock_time = oldest + self.window
        
        remaining = (unlock_time - now).total_seconds()
        return max(0, int(remaining))
