from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import RetrievalCacheEntry


class Cache:
    """Small database-backed cache for public page retrieval.

    Successful responses live longer than failures so transient errors do not
    prevent a later retry for too long.
    """

    def __init__(
        self,
        db: Session,
        success_ttl_seconds: int = 60 * 60 * 24,
        error_ttl_seconds: int = 60 * 15,
    ) -> None:
        self.db = db
        self.success_ttl = timedelta(seconds=success_ttl_seconds)
        self.error_ttl = timedelta(seconds=error_ttl_seconds)

    def get(self, url: str) -> Optional[RetrievalCacheEntry]:
        entry = self.db.get(RetrievalCacheEntry, url)
        if entry is None:
            return None

        if entry.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            self.db.delete(entry)
            self.db.commit()
            return None

        return entry

    def set(
        self,
        url: str,
        *,
        final_url: Optional[str] = None,
        status_code: Optional[int] = None,
        content_type: Optional[str] = None,
        content: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> RetrievalCacheEntry:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        is_error = bool(error) or (status_code is not None and status_code >= 400)
        ttl = self.error_ttl if is_error else self.success_ttl

        entry = self.db.get(RetrievalCacheEntry, url)
        if entry is None:
            entry = RetrievalCacheEntry(url=url)
            self.db.add(entry)

        entry.final_url = final_url
        entry.status_code = status_code
        entry.content_type = content_type
        entry.content = content
        entry.error = error
        entry.extra = extra or {}
        entry.fetched_at = now
        entry.expires_at = now + ttl

        self.db.commit()
        self.db.refresh(entry)
        return entry
