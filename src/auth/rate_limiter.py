#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Rate limiting for login attempts.
#
"""
Rate limiting for login attempts.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List


class LoginRateLimiter:
    """
    Brute-force protection for login.
    
    Limits login attempts per username within a time window.
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        """
        Initializes the rate limiter.
        
        Args:
            max_attempts: Maximum attempts within the time window
            window_minutes: Time window in minutes
        """
        self.attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
    
    def is_allowed(self, username: str) -> bool:
        """
        Checks whether a login attempt is allowed.
        
        Args:
            username: DB username
            
        Returns:
            True if login is allowed
        """
        now = datetime.now()
        
        # Remove old attempts (outside the time window)
        self.attempts[username] = [
            ts for ts in self.attempts[username]
            if now - ts < self.window
        ]
        
        # Too many attempts?
        if len(self.attempts[username]) >= self.max_attempts:
            return False
        
        return True
    
    def record_attempt(self, username: str) -> None:
        """
        Records a login attempt.
        
        Args:
            username: DB username
        """
        self.attempts[username].append(datetime.now())
    
    def reset(self, username: str) -> None:
        """
        Resets login attempts for a username.
        
        Args:
            username: DB username
        """
        if username in self.attempts:
            del self.attempts[username]
    
    def get_remaining_attempts(self, username: str) -> int:
        """
        Returns remaining login attempts.
        
        Args:
            username: DB username
            
        Returns:
            Number of remaining attempts
        """
        now = datetime.now()
        
        # Current attempts within the time window
        recent_attempts = [
            ts for ts in self.attempts.get(username, [])
            if now - ts < self.window
        ]
        
        return max(0, self.max_attempts - len(recent_attempts))
    
    def get_retry_after(self, username: str) -> int:
        """
        Returns seconds until the next allowed attempt.
        
        Args:
            username: DB username
            
        Returns:
            Seconds until unlock (0 if allowed)
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
        
        # Oldest attempt + window = unlock time
        oldest = min(recent_attempts)
        unlock_time = oldest + self.window
        
        remaining = (unlock_time - now).total_seconds()
        return max(0, int(remaining))
