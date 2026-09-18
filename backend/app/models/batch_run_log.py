from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BatchRunLog(Base):
    """일일 데이터 수집 배치 실행 로그. job_name별 실행 1회당 1행."""

    __tablename__ = "batch_run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    job_name: Mapped[str] = mapped_column(String(50), index=True)  # 예: "onbid_auction", "naver_news"
    status: Mapped[str] = mapped_column(String(20))  # "success" | "partial_failure" | "failed"

    collected_count: Mapped[int] = mapped_column(Integer, default=0)  # 수집 건수(신규 저장분)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)  # 중복으로 건너뛴 건수
    fail_count: Mapped[int] = mapped_column(Integer, default=0)  # 실패 건수

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
