from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppraisalCase(Base):
    """감정평가서에서 파싱한 거래사례/감정평가사례 1건 (기능3 유사사례 검색용 메타데이터)."""

    __tablename__ = "appraisal_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    source_file: Mapped[str] = mapped_column(String(255), index=True)
    case_type: Mapped[str] = mapped_column(String(20))  # "거래사례" | "감정평가사례"
    code: Mapped[str] = mapped_column(String(5))  # 문서 내 기호 (ㄱ, a 등)

    sido: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sigungu: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    dong: Mapped[str] = mapped_column(String(50))
    jibun: Mapped[str | None] = mapped_column(String(30), nullable=True)
    complex_name: Mapped[str] = mapped_column(String(120))
    dong_ho: Mapped[str | None] = mapped_column(String(50), nullable=True)

    usage: Mapped[str] = mapped_column(String(30))
    exclusive_area: Mapped[float] = mapped_column(Float)

    event_date: Mapped[str] = mapped_column(String(10))  # 거래일자 또는 기준시점, YYYY-MM-DD
    purpose: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 감정평가목적 (시가참고/담보)
    amount: Mapped[int] = mapped_column(Integer)  # 만원
    unit_price: Mapped[int] = mapped_column(Integer)  # 만원/㎡
    location_note: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 복층/단층/위치 등
    approval_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 사용승인일

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
