from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RtechRealTransaction(Base):
    """부동산테크 실거래가 내역. (단지, 거래일, 면적, 거래금액, 거래유형) 조합 기준 중복 방지.

    개별 거래를 고유하게 식별할 자연키가 API 응답에 없어(동/호수 비공개) 이 조합을 대리키로 쓴다 -
    같은 날 같은 면적·같은 금액의 서로 다른 두 건은 하나로 합쳐질 수 있음(프로토타입 수준 한계).
    """

    __tablename__ = "rtech_real_transactions"
    __table_args__ = (
        UniqueConstraint("rtech_complex_id", "deal_ymd", "area", "deal_amount", "trade_mode", name="uq_rtech_real_txn_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    rtech_complex_id: Mapped[int] = mapped_column(ForeignKey("rtech_complexes.id"), index=True)

    trade_mode: Mapped[str] = mapped_column(String(20))  # 원본 TRADE_MODE 그대로 저장 (관측값: "RENT")
    deal_ymd: Mapped[str] = mapped_column(String(10), index=True)  # M_DEAL_YMD (YYYY-MM-DD)
    deal_amount: Mapped[int] = mapped_column(Integer)  # M_DEAL_AMT, 만원
    area: Mapped[float] = mapped_column(Float)  # BLDG_AREA, ㎡

    source: Mapped[str] = mapped_column(String(20), default="rtech_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
