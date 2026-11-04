import threading
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import UsageLimit

_manager_lock = threading.Lock()


class UsageLimitExceeded(Exception):
    """Raised when the VENTRIX analysis limit has been reached."""


class UsageLimitManager:
    def __init__(self, max_analyses: Optional[int] = None, scope: str = "global", scope_id: Optional[str] = None):
        self.max_analyses = max_analyses if max_analyses is not None else settings.MAX_ANALYSES
        self.scope = scope
        self.scope_id = scope_id

    def _get_or_create_row(self, db: Session) -> UsageLimit:
        row = (
            db.query(UsageLimit)
            .filter(UsageLimit.scope == self.scope, UsageLimit.scope_id == self.scope_id)
            .with_for_update()
            .first()
        )
        if row is None:
            row = UsageLimit(
                scope=self.scope,
                scope_id=self.scope_id,
                max_analyses=self.max_analyses,
                used_analyses=0,
                reserved_count=0,
            )
            db.add(row)
            db.flush()
        if row.max_analyses != self.max_analyses:
            row.max_analyses = self.max_analyses
        return row

    def get_usage(self, db: Session) -> Dict[str, Any]:
        with _manager_lock:
            with db.begin():
                row = self._get_or_create_row(db)
                completed = row.used_analyses or 0
                reserved = row.reserved_count or 0
                remaining = max(0, row.max_analyses - completed - reserved)
                return {
                    "scope": self.scope,
                    "scope_id": self.scope_id,
                    "max_analyses": row.max_analyses,
                    "completed_analyses": completed,
                    "reserved_analyses": reserved,
                    "remaining_analyses": remaining,
                    "limit_reached": completed + reserved >= row.max_analyses,
                }

    def can_start_analysis(self, db: Session) -> bool:
        usage = self.get_usage(db)
        return not usage["limit_reached"]

    def reserve_analysis(self, db: Session) -> None:
        with _manager_lock:
            with db.begin():
                row = self._get_or_create_row(db)
                if (row.used_analyses or 0) + (row.reserved_count or 0) >= row.max_analyses:
                    raise UsageLimitExceeded(
                        f"Maximum analysis limit of {row.max_analyses} successful runs has been reached."
                    )
                row.reserved_count = (row.reserved_count or 0) + 1

    def complete_analysis(self, db: Session, success: bool) -> None:
        with _manager_lock:
            with db.begin():
                row = self._get_or_create_row(db)
                if (row.reserved_count or 0) > 0:
                    row.reserved_count -= 1
                if success:
                    row.used_analyses = (row.used_analyses or 0) + 1

    # Compatibility aliases
    def check_and_reserve(self, db: Session) -> None:
        self.reserve_analysis(db)

    def release(self, db: Session, success: bool) -> None:
        self.complete_analysis(db, success)

    def check_limit(self, db: Session) -> bool:
        return self.can_start_analysis(db)

    def increment(self, db: Session) -> None:
        self.reserve_analysis(db)

    def decrement(self, db: Session, success: bool = False) -> None:
        self.complete_analysis(db, success)
