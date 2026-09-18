from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsArticle(Base):
    """네이버 뉴스 검색 API로 수집한 부동산 정책 관련 뉴스 원본. link 기준으로 중복 저장을 방지한다."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    link: Mapped[str] = mapped_column(String(500), unique=True, index=True)  # 기사 링크(중복체크 키)
    original_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pub_date: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 원본 RFC822 문자열 그대로 저장

    search_keyword: Mapped[str] = mapped_column(String(100))  # 수집에 사용한 검색어

    source: Mapped[str] = mapped_column(String(20), default="naver_news_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
