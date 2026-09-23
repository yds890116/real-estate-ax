from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourtAuctionItem(Base):
    """법원경매정보(courtauction.go.kr) 물건상세검색 원본 데이터. docid(법원경매정보 자체 고유 식별자) 기준으로 중복 저장을 방지한다."""

    __tablename__ = "court_auction_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    docid: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # 법원경매정보 고유 행 식별자(중복체크 키)
    case_no: Mapped[str] = mapped_column(String(30), index=True)  # 사건번호 (예: 2018타경6939)
    item_no: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 물건번호

    court_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 법원명
    dept_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 담당계

    usage_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # 물건종류(용도)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 소재지
    building_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 건물 구조/면적 상세
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 비고

    appraisal_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 감정평가액(원)
    min_sale_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 최저매각가격(원)
    min_sale_price_rate: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 최저매각가율(%, 감정가 대비)
    failed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 유찰횟수

    sale_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 매각기일 YYYYMMDD
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 진행상태(신건/유찰 N회 등)

    source: Mapped[str] = mapped_column(String(20), default="court_auction_live")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
