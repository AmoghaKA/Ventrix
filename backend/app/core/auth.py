"""Authentication helpers for verifying Supabase access tokens."""

from typing import Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_security = HTTPBearer(auto_error=False)


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    return str(user_id)