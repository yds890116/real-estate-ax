from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.regional_stats import (
    LIVE_NOTICE,
    SAMPLE_NOTICE,
    RegionalBidStatItem,
    RegionalBidStatSummary,
    RegionalBidStatTrend,
    RegionalStatsIngestResult,
)
from app.services.regional_stats_service import collect_onbid_regional_stats, get_region_list, get_regional_summary, get_regional_trend

router = APIRouter()


@router.get("/regions", response_model=list[str])
def list_regions(db: Session = Depends(get_db)):
    """지역별 입찰 통계 화면의 지역 선택 드롭다운용 시도 목록."""
    return get_region_list(db)


@router.get("/trend", response_model=RegionalBidStatTrend)
def get_trend(sido: str, sigungu: str | None = None, db: Session = Depends(get_db)):
    """지역 선택 시 최근 입찰 건수·낙찰률·평균 낙찰가율 추이."""

    rows, source, is_sample = get_regional_trend(db, sido, sigungu)
    return RegionalBidStatTrend(
        sido=sido,
        sigungu=sigungu,
        items=[RegionalBidStatItem.model_validate(r) for r in rows],
        source=source,
        is_sample_data=is_sample,
        notice=SAMPLE_NOTICE if is_sample else LIVE_NOTICE,
    )


@router.get("/summary", response_model=RegionalBidStatSummary)
def get_summary(sido: str, sigungu: str | None = None, db: Session = Depends(get_db)):
    """종합분석 화면의 입찰통계 요약 카드용 - 해당 지역 가장 최근 1건."""

    latest, source, is_sample = get_regional_summary(db, sido, sigungu)
    return RegionalBidStatSummary(
        sido=sido,
        sigungu=sigungu,
        latest=RegionalBidStatItem.model_validate(latest) if latest else None,
        source=source,
        is_sample_data=is_sample,
        notice=SAMPLE_NOTICE if is_sample else LIVE_NOTICE,
    )


@router.post("/run", response_model=RegionalStatsIngestResult)
def run_collection_now(inq_perd: str | None = None, stats_type_cd: str | None = None, db: Session = Depends(get_db)):
    """온비드 지역별 입찰 통계 실제 API 수집을 즉시 1회 실행한다 (테스트/데모용 수동 트리거).

    inq_perd 생략 시 이번 달(YYYYMM)을 조회한다. 서비스/오퍼레이션명이 확정되기 전까지는
    항상 실패로 기록되며, 실패 사유가 결과에 명확히 남는다.
    """

    inq_perd = inq_perd or date.today().strftime("%Y%m")
    result = collect_onbid_regional_stats(db, inq_perd, stats_type_cd=stats_type_cd)
    return RegionalStatsIngestResult(**result)
