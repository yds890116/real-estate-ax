from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardItem
from app.services.dashboard_service import build_dashboard

router = APIRouter()


@router.get("", response_model=list[DashboardItem])
def get_dashboard(db: Session = Depends(get_db)):
    """등록된 전 물건에 대한 시세·리스크·권리·유사사례 요약과 이상 매물 알림."""

    return build_dashboard(db)
