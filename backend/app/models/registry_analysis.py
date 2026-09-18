from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegistryAnalysis(Base):
    """업로드된 등기부등본 1건의 파싱·분석 결과."""

    __tablename__ = "registry_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True, index=True)

    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))  # "pdf" | "image"

    raw_text: Mapped[str] = mapped_column(Text)
    rights: Mapped[list] = mapped_column(JSON)  # list[dict] — RegistryRight 직렬화
    risk_flags: Mapped[list] = mapped_column(JSON)  # list[str]

    summary: Mapped[str] = mapped_column(Text)
    generation_method: Mapped[str] = mapped_column(String(10))  # "llm" | "template"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
