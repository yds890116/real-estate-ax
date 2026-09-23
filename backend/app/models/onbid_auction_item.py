from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OnbidAuctionItem(Base):
    """온비드 공매 물건 원본 데이터. cltr_mnmt_no(물건관리번호) 기준으로 중복 저장을 방지한다."""

    __tablename__ = "onbid_auction_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    cltr_mnmt_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # 물건관리번호(중복체크 키)
    plnm_no: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 공고번호
    pbct_no: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 공매번호

    cltr_nm: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 물건명
    ctgr_full_nm: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 용도(카테고리)
    ldnm_adrs: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 소재지(지번)
    nmrd_adrs: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 소재지(도로명)

    dpsl_mtd_nm: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 처분방식(매각/임대 등)
    bid_mtd_nm: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 입찰방식

    min_bid_prc: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 최저입찰가(원)
    apsl_ases_avg_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 감정가(원)
    fee_rate: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 최저입찰가율(%), 원본 표기 그대로 저장

    pbct_begn_dtm: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 입찰 시작일시
    pbct_cls_dtm: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 입찰 마감일시
    pbct_cltr_stat_nm: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 물건상태
    uscbd_cnt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 유찰횟수

    # 감정평가 기준정보 (통합용도별물건감정평가서정보상세 - 신규 물건 수집 시 best-effort로 채움)
    appraisal_amt: Mapped[int | None] = mapped_column(Integer, nullable=True)  # APSL_ASES_AMT, 원
    appraisal_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # APSL_ASES_DT
    appraisal_org_nm: Mapped[str | None] = mapped_column(String(120), nullable=True)  # APSL_ASES_ORG_NM

    source: Mapped[str] = mapped_column(String(20), default="onbid_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
