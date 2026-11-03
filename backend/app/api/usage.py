from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.usage_manager import UsageLimitManager

router = APIRouter(tags=["usage"])


@router.get("/system/usage")
def get_system_usage(db: Session = Depends(get_db)):
    return UsageLimitManager().get_usage(db)
