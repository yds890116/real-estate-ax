from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    address: Mapped[str] = mapped_column(String(255))
    sido: Mapped[str] = mapped_column(String(50), index=True)
    sigungu: Mapped[str] = mapped_column(String(50), index=True)
    dong: Mapped[str | None] = mapped_column(String(50), nullable=True)

    property_type: Mapped[str] = mapped_column(String(30))  # 아파트/오피스텔/연립다세대 등
    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    exclusive_area: Mapped[float] = mapped_column(Float)  # 전용면적(m2)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    household_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 단지 세대수

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
