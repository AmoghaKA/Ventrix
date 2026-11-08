from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.services.usage_manager import UsageLimitManager

router = APIRouter(tags=["usage"])


@router.get("/system/usage")
def get_system_usage(
    db: Session = Depends(get_db),
    user_id = Depends(get_current_user_id),
):
    scope_id = user_id or "anonymous"
    return UsageLimitManager(scope="user", scope_id=scope_id).get_usage(db)
