from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionalBidStat(Base):
    """온비드 지역별 입찰 통계. (sido, sigungu, period, stats_type_cd) 조합 기준으로 중복 저장을 방지한다.

    source="onbid_stats_api"는 실제 API 수집분, source="sample"은 API 미가동 시 화면·로직 검증용
    샘플 데이터임을 나타낸다 (CLAUDE.md: 공식 API 연동 전/중 단계에서는 샘플 데이터로 우선 구현).
    """

    __tablename__ = "regional_bid_stats"
    __table_args__ = (UniqueConstraint("sido", "sigungu", "period", "stats_type_cd", name="uq_regional_bid_stat_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    sido: Mapped[str] = mapped_column(String(50), index=True)
    sigungu: Mapped[str | None] = mapped_column(String(50), nullable=True)

    period: Mapped[str] = mapped_column(String(10), index=True)  # YYYY | YYYYMM | YYYY-Q
    period_type: Mapped[str] = mapped_column(String(10))  # "year" | "month" | "quarter"
    stats_type_cd: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 재산유형 통계코드

    bid_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 입찰건수
    win_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 낙찰건수
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 낙찰률(%)

    avg_appraisal_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 평균 감정가(백만원)
    avg_min_bid_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 평균 최저입찰가(백만원)
    avg_win_bid_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 평균 낙찰가(백만원)

    avg_bid_rate_vs_appraisal: Mapped[float | None] = mapped_column(Float, nullable=True)  # 평균 낙찰가율(감정가 대비, %)
    avg_bid_rate_vs_min_bid: Mapped[float | None] = mapped_column(Float, nullable=True)  # 평균 낙찰가율(최저입찰가 대비, %)

    bidder_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 입찰참가자수
    competition_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 경쟁률

    source: Mapped[str] = mapped_column(String(20))  # "onbid_stats_api" | "sample"
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
