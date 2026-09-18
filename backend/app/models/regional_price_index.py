from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionalPriceIndex(Base):
    """한국부동산원 R-ONE 지역별 주택가격지수. (statbl_id, region_cd, period) 조합 기준 중복 방지.

    시세 추정 엔진의 보조 피처(지역 트렌드 지표)로 쓸 수 있도록 지역·시점별 지수를 그대로 적재한다.
    index_type: "actual_transaction"(실거래 신고 기반) | "price_trend"(표본조사 기반, 전국주택가격동향조사)
    trade_type: "sale"(매매) | "jeonse"(전세)
    """

    __tablename__ = "regional_price_indices"
    __table_args__ = (UniqueConstraint("statbl_id", "region_cd", "period", name="uq_regional_price_index_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    statbl_id: Mapped[str] = mapped_column(String(30), index=True)
    index_type: Mapped[str] = mapped_column(String(20))  # "actual_transaction" | "price_trend"
    trade_type: Mapped[str] = mapped_column(String(10))  # "sale" | "jeonse"

    period: Mapped[str] = mapped_column(String(6), index=True)  # YYYYMM

    region_cd: Mapped[int] = mapped_column(Integer, index=True)  # CLS_ID
    region_name: Mapped[str] = mapped_column(String(50))  # CLS_NM (예: "강남구")
    region_full_name: Mapped[str] = mapped_column(String(200))  # CLS_FULLNM (예: "서울>강남서초권>강남구")

    index_value: Mapped[float] = mapped_column(Float)  # DTA_VAL

    source: Mapped[str] = mapped_column(String(20), default="rone_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
