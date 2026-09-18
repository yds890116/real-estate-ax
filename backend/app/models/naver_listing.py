from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NaverListing(Base):
    """스크래핑(또는 폴백 샘플)으로 수집한 네이버 부동산 매물 1건."""

    __tablename__ = "naver_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    complex_name: Mapped[str] = mapped_column(String(120), index=True)
    sigungu: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    exclusive_area: Mapped[float] = mapped_column(Float)
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trade_type: Mapped[str] = mapped_column(String(10))  # "매매" | "전세" | "월세"
    price: Mapped[int] = mapped_column(Integer)  # 만원 (매매가 또는 보증금)
    monthly_rent: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 만원
    realtor: Mapped[str | None] = mapped_column(String(60), nullable=True)
    listed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 매물 등록일, YYYY-MM-DD

    source: Mapped[str] = mapped_column(String(20))  # "naver_scrape" | "sample"
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
