from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RtechPriceQuote(Base):
    """부동산테크 평형별 매매/전세 시세(주간 발표 하한~상한가). (단지, 전용면적, 기준일) 기준 중복 방지."""

    __tablename__ = "rtech_price_quotes"
    __table_args__ = (UniqueConstraint("rtech_complex_id", "priv_area", "base_date", name="uq_rtech_price_quote_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    rtech_complex_id: Mapped[int] = mapped_column(ForeignKey("rtech_complexes.id"), index=True)
    pyong_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)  # KTECH_PYONG_SEQ

    pyong: Mapped[float] = mapped_column(Float)
    priv_area: Mapped[float] = mapped_column(Float)  # 전용면적(㎡)
    base_date: Mapped[str] = mapped_column(String(10), index=True)  # APTP_DATE (YYYY-MM-DD)

    sale_lower_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # S_LOWER_PRICE, 만원
    sale_upper_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # S_UPPER_PRICE, 만원
    jeonse_lower_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # R_LOWER_PRICE, 만원
    jeonse_upper_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # R_UPPER_PRICE, 만원

    household_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # HOUSE_CNT (해당 평형 세대수)

    source: Mapped[str] = mapped_column(String(20), default="rtech_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
