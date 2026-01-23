"""
Admin authentication module for Gloorbot Coordinator.
Provides simple session-based authentication for admin features.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from typing import Dict

# Admin credentials
#
# Production: set these via env vars.
# Local/dev fallback: defaults exist to preserve existing behavior.
_DEFAULT_ADMIN_EMAIL = "93robingattis@gmail.com"
_DEFAULT_ADMIN_PASSWORD = "Alphonse5150$"

ADMIN_EMAIL = os.getenv("GLOORBOT_ADMIN_EMAIL", _DEFAULT_ADMIN_EMAIL).strip()
ADMIN_PASSWORD = os.getenv("GLOORBOT_ADMIN_PASSWORD", _DEFAULT_ADMIN_PASSWORD)

# Session storage (in-memory for simplicity; use Redis in production)
_sessions: Dict[str, dict] = {}
SESSION_DURATION = timedelta(hours=24)


def verify_credentials(email: str, password: str) -> bool:
    """Verify admin credentials."""
    return email == ADMIN_EMAIL and password == ADMIN_PASSWORD


def create_session(email: str) -> str:
    """Create a new admin session and return the session token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "email": email,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + SESSION_DURATION,
    }
    return token


def verify_session(token: str | None) -> bool:
    """Verify if a session token is valid and not expired."""
    if not token or token not in _sessions:
        return False
    
    session = _sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        # Session expired, clean it up
        del _sessions[token]
        return False
    
    return True


def invalidate_session(token: str) -> None:
    """Invalidate a session token (logout)."""
    if token in _sessions:
        del _sessions[token]


def cleanup_expired_sessions() -> None:
    """Remove all expired sessions from memory."""
    now = datetime.utcnow()
    expired = [token for token, session in _sessions.items() if now > session["expires_at"]]
    for token in expired:
        del _sessions[token]
