from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rone_index import RegionTrendFeatures, RoneTableIngestResult
from app.services.rone_index_service import collect_regional_price_indices, get_region_trend_features

router = APIRouter()


@router.post("/run", response_model=list[RoneTableIngestResult])
def run_collection_now(months_back: int = 6, db: Session = Depends(get_db)):
    """R-ONE 지역별 공동주택 실거래가격지수·매매/전세가격지수 수집을 즉시 1회 실행한다 (테스트/데모용)."""

    results = collect_regional_price_indices(db, months_back=months_back)
    return [RoneTableIngestResult(**r) for r in results]


@router.get("/trend", response_model=RegionTrendFeatures)
def get_trend(sido: str, sigungu: str | None = None, db: Session = Depends(get_db)):
    """시세 추정 엔진의 보조 피처로 쓸 수 있는 지역 트렌드 지수 요약(최신값 + 전월 대비 변동률)."""

    features = get_region_trend_features(db, sido, sigungu)
    return RegionTrendFeatures(**features)
