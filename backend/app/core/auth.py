"""Authentication helpers for verifying Supabase access tokens."""

import time
from typing import Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_security = HTTPBearer(auto_error=False)

# Short-lived in-memory cache for validated Supabase access tokens. This avoids
# a network round trip to Supabase on every authenticated request.
_AUTH_CACHE_TTL_SECONDS = 300.0
_auth_cache: dict[str, tuple[str, float]] = {}


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> Optional[str]:
    """Return the Supabase user id (sub) for the bearer token.

    Anonymous requests (no bearer token) are allowed and return ``None`` so that
    local development, demos, and tests can run without authentication. When a
    token is supplied it is validated against Supabase.
    """
    if credentials is None or not credentials.credentials:
        return None

    token = credentials.credentials
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        # Auth backend not configured: treat as anonymous instead of failing.
        return None

    now = time.time()
    cached = _auth_cache.get(token)
    if cached is not None and cached[1] > now:
        return cached[0]

    try:
        response = requests.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
            timeout=10,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if response.status_code != 200:
        _auth_cache.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        _auth_cache.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    _auth_cache[token] = (str(user_id), now + _AUTH_CACHE_TTL_SECONDS)
    if len(_auth_cache) > 1024:
        for key, (_, expires_at) in list(_auth_cache.items()):
            if expires_at <= now:
                _auth_cache.pop(key, None)
    return str(user_id)