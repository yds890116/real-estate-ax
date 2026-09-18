from pydantic import BaseModel

SAMPLE_NOTICE = (
    "온비드 지역별 입찰 통계 API 연동을 준비 중입니다(서비스/오퍼레이션명 확정 필요, 개발 환경에서는 "
    "openapi.onbid.co.kr 접속 자체가 차단되어 있어 실호출 검증 전입니다). 화면 검증용 참고 샘플 데이터입니다."
)
LIVE_NOTICE = "온비드 지역별 입찰 통계 API로 수집한 데이터입니다."


class RegionalBidStatItem(BaseModel):
    id: int
    sido: str
    sigungu: str | None
    period: str
    period_type: str
    bid_count: int | None
    win_count: int | None
    win_rate: float | None
    avg_appraisal_amt: int | None
    avg_min_bid_amt: int | None
    avg_win_bid_amt: int | None
    avg_bid_rate_vs_appraisal: float | None
    avg_bid_rate_vs_min_bid: float | None
    bidder_count: int | None
    competition_rate: float | None
    source: str

    class Config:
        from_attributes = True


class RegionalBidStatTrend(BaseModel):
    sido: str
    sigungu: str | None
    items: list[RegionalBidStatItem]
    source: str  # "onbid_stats_api" | "sample"
    is_sample_data: bool
    notice: str


class RegionalBidStatSummary(BaseModel):
    """종합분석 화면 요약 카드용 - 해당 지역의 가장 최근 1건."""

    sido: str
    sigungu: str | None
    latest: RegionalBidStatItem | None
    source: str
    is_sample_data: bool
    notice: str


class RegionOption(BaseModel):
    sido: str


class RegionalStatsIngestResult(BaseModel):
    collected: int
    skipped: int
    failed: int
    status: str
    error: str | None = None
