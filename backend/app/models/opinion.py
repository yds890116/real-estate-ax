from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewOpinion(Base):
    """물건 1건당 심사의견 초안(AI) + 심사역 최종본 + 수정 이력.

    ai_draft는 마지막으로 생성된 AI 초안 원문(불변, 비교 기준)이고 current_content가
    현재 화면에 보이는 최종본이다. 저장할 때마다 이전 current_content를 edit_history에
    적재해 "AI 초안 vs 심사역 최종본" 비교와 수정 이력 추적이 가능하게 한다.
    """

    __tablename__ = "review_opinions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), unique=True, index=True)

    ai_draft: Mapped[str] = mapped_column(Text)
    current_content: Mapped[str] = mapped_column(Text)
    edit_history: Mapped[list] = mapped_column(JSON, default=list)  # list[{"content": str, "saved_at": str}]
    generation_method: Mapped[str] = mapped_column(String(10))  # "llm" | "template"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
