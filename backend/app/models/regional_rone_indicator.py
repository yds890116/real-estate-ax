from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegionalRoneIndicator(Base):
    """R-ONE 지가변동률·임대동향지수 등 단일값 지표. (statbl_id, region_cd, period) 기준 중복 방지.

    RegionalPriceIndex(매매/전세 지수, 하한~상한 없음/단일값 지수)와 달리 이 지표들은 값 하나
    (변동률 또는 지수)만 가지므로 별도의 범용 테이블로 둔다.
    """

    __tablename__ = "regional_rone_indicators"
    __table_args__ = (UniqueConstraint("statbl_id", "region_cd", "period", name="uq_regional_rone_indicator_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    statbl_id: Mapped[str] = mapped_column(String(30), index=True)
    indicator_type: Mapped[str] = mapped_column(String(30), index=True)  # "land_price_change_rate" | "rental_price_index"

    period: Mapped[str] = mapped_column(String(10), index=True)  # YYYYMM | YYYY-Q
    period_type: Mapped[str] = mapped_column(String(10))  # "month" | "quarter"

    region_cd: Mapped[int] = mapped_column(Integer, index=True)  # CLS_ID
    region_name: Mapped[str] = mapped_column(String(50))
    region_full_name: Mapped[str] = mapped_column(String(200))

    value: Mapped[float] = mapped_column(Float)  # DTA_VAL (변동률 % 또는 지수)
    unit: Mapped[str] = mapped_column(String(20))  # UI_NM (예: "%", "지수")

    source: Mapped[str] = mapped_column(String(20), default="rone_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
