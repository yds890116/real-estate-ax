from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketTransaction(Base):
    """정제된 실거래가 레코드. 국토부 API 수집분(source=molit_api) 등을 누적 저장한다."""

    __tablename__ = "market_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    sido: Mapped[str] = mapped_column(String(50), index=True)
    sigungu: Mapped[str] = mapped_column(String(50), index=True)
    dong: Mapped[str | None] = mapped_column(String(50), nullable=True)
    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    exclusive_area: Mapped[float] = mapped_column(Float)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deal_price: Mapped[int] = mapped_column(Integer)  # 만원
    deal_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD

    source: Mapped[str] = mapped_column(String(20), default="molit_api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
