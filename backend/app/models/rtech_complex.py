from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RtechComplex(Base):
    """부동산테크(rtech.or.kr) 단지 마스터. rtech_apt_seq(원본 SEQ) 기준으로 중복 저장을 방지한다.

    market_transactions.complex_name과의 매칭은 별도 매핑 테이블 없이 (sigungu, complex_name)
    문자열 일치로 조회 시점에 수행한다 (app/services/rtech_comparison_service.py).
    """

    __tablename__ = "rtech_complexes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    rtech_apt_seq: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    apt_name: Mapped[str] = mapped_column(String(120), index=True)

    sido: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sigungu: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    dong: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)  # JUSO(지번)
    road_address: Mapped[str | None] = mapped_column(String(255), nullable=True)  # NJUSO(도로명)
    addr_code: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 10자리 법정동코드

    household_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # APT_H_NUM
    dong_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # APT_TOT_DONG
    min_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_approval_ym: Mapped[str | None] = mapped_column(String(20), nullable=True)  # USEAPR_YM (예: "2003년11월")
    area_range: Mapped[str | None] = mapped_column(String(50), nullable=True)  # PRIV_AREA_AROUND (예: "28.1㎡~58.78㎡")

    x_coord: Mapped[float | None] = mapped_column(Float, nullable=True)  # TM 좌표
    y_coord: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str] = mapped_column(String(20), default="rtech_api")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
