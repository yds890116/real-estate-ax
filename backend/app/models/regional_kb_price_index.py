from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionalKbPriceIndex(Base):
    """KB부동산 데이터허브 주택가격동향조사 - 매매/전세/월세 가격지수. (region_cd, trade_type, period) 기준 중복 방지.

    region_cd는 KB 자체 지역코드로 숫자뿐 아니라 영문이 섞인 코드도 있다(예: "1A0000"=강북14개구).
    """

    __tablename__ = "regional_kb_price_indices"
    __table_args__ = (UniqueConstraint("region_cd", "trade_type", "period", name="uq_regional_kb_price_index_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    region_cd: Mapped[str] = mapped_column(String(20), index=True)  # KB 지역코드 (예: "1100000000", "1A0000")
    region_name: Mapped[str] = mapped_column(String(50), index=True)  # 예: "서울"

    housing_type: Mapped[str] = mapped_column(String(20))  # "주택종합" | "아파트"(월세 전용)
    trade_type: Mapped[str] = mapped_column(String(10))  # "매매" | "전세" | "월세"

    period: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM

    index_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 전월 대비 증감률(%)

    source: Mapped[str] = mapped_column(String(20), default="kb_land_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
