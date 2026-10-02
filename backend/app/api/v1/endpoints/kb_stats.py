from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.kb_stats import KbPriceTrendResponse, KbStatsIngestResult
from app.services.kb_stats_service import collect_kb_price_indices, get_kb_price_trend

router = APIRouter()


@router.post("/run", response_model=list[KbStatsIngestResult])
def run_collection_now(db: Session = Depends(get_db)):
    """KB부동산 데이터허브 매매/전세/월세 가격지수 수집을 즉시 1회 실행한다 (테스트/데모용 수동 트리거)."""

    results = collect_kb_price_indices(db)
    return [KbStatsIngestResult(**r) for r in results]


@router.get("/trend", response_model=KbPriceTrendResponse)
def get_trend(sido: str, months: int = 24, db: Session = Depends(get_db)):
    """시도 단위 KB 매매/전세/월세 가격지수 최근 N개월 시계열 (차트용)."""

    result = get_kb_price_trend(db, sido, months=months)
    return KbPriceTrendResponse(**result)
