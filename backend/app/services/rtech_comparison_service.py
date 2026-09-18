"""부동산테크 시세·실거래가와 국토교통부 실거래가를 같은 단지·평형 기준으로 비교한다 (요구사항 5·6).

매칭은 별도 매핑 테이블 없이 (sigungu, 정규화한 단지명) 문자열 일치로 조회 시점에 수행한다 -
listing_comparison.py(네이버 매물 vs 국토부 실거래가 비교)와 같은 방식이다. 두 소스의 단지명
표기가 완전히 같지 않을 수 있어(예: "래미안대치팰리스" vs "래미안대치팰리스1단지") 이 매칭은
프로토타입 수준이며, 필요 시 향후 별도 매핑 테이블로 고도화할 수 있다.
"""

from sqlalchemy.orm import Session

from app.models.market_transaction import MarketTransaction
from app.models.rent_transaction import RentTransaction
from app.models.rtech_complex import RtechComplex
from app.models.rtech_price_quote import RtechPriceQuote
from app.models.rtech_real_transaction import RtechRealTransaction

AREA_TOLERANCE_SQM = 3.0  # listing_comparison.py와 동일 기준


def _normalize(name: str) -> str:
    return name.replace(" ", "").strip()


def find_complex(db: Session, complex_name: str, sigungu: str | None = None) -> RtechComplex | None:
    query = db.query(RtechComplex)
    if sigungu:
        query = query.filter(RtechComplex.sigungu == sigungu)

    candidates = query.all()
    target = _normalize(complex_name)
    for c in candidates:
        if _normalize(c.apt_name) == target:
            return c
    for c in candidates:  # 부분 일치 폴백 (예: "래미안대치팰리스" in "래미안대치팰리스1단지")
        if target in _normalize(c.apt_name) or _normalize(c.apt_name) in target:
            return c
    return None


def _latest_price_quotes(db: Session, rtech_complex_id: int) -> list[RtechPriceQuote]:
    all_rows = (
        db.query(RtechPriceQuote)
        .filter(RtechPriceQuote.rtech_complex_id == rtech_complex_id)
        .order_by(RtechPriceQuote.base_date.desc())
        .all()
    )
    latest_by_area: dict[float, RtechPriceQuote] = {}
    for row in all_rows:
        if row.priv_area not in latest_by_area:
            latest_by_area[row.priv_area] = row
    return sorted(latest_by_area.values(), key=lambda r: r.priv_area)


def _molit_sale_stats(db: Session, sigungu: str, complex_name: str, priv_area: float) -> tuple[int | None, int]:
    rows = (
        db.query(MarketTransaction)
        .filter(
            MarketTransaction.sigungu == sigungu,
            MarketTransaction.complex_name == complex_name,
            MarketTransaction.exclusive_area >= priv_area - AREA_TOLERANCE_SQM,
            MarketTransaction.exclusive_area <= priv_area + AREA_TOLERANCE_SQM,
        )
        .all()
    )
    if not rows:
        return None, 0
    avg_price = round(sum(r.deal_price for r in rows) / len(rows))
    return avg_price, len(rows)


def _molit_jeonse_stats(db: Session, sigungu: str, complex_name: str, priv_area: float) -> tuple[int | None, int]:
    rows = (
        db.query(RentTransaction)
        .filter(
            RentTransaction.sigungu == sigungu,
            RentTransaction.complex_name == complex_name,
            RentTransaction.contract_type == "전세",
            RentTransaction.exclusive_area >= priv_area - AREA_TOLERANCE_SQM,
            RentTransaction.exclusive_area <= priv_area + AREA_TOLERANCE_SQM,
        )
        .all()
    )
    if not rows:
        return None, 0
    avg_deposit = round(sum(r.deposit for r in rows) / len(rows))
    return avg_deposit, len(rows)


def compare_complex(db: Session, complex_name: str, sigungu: str | None = None) -> dict | None:
    """단지명(+선택 시군구)으로 부동산테크·국토부 데이터를 찾아 평형별 나란히 비교한 결과를 반환한다.

    부동산테크에 해당 단지가 없으면 None을 반환한다(호출부에서 404 처리)."""

    rtech_complex = find_complex(db, complex_name, sigungu)
    if rtech_complex is None:
        return None

    quotes = _latest_price_quotes(db, rtech_complex.id)
    target_sigungu = rtech_complex.sigungu or sigungu or ""

    items = []
    for q in quotes:
        molit_sale_avg, molit_sale_count = _molit_sale_stats(db, target_sigungu, complex_name, q.priv_area)
        molit_jeonse_avg, molit_jeonse_count = _molit_jeonse_stats(db, target_sigungu, complex_name, q.priv_area)

        rtech_sale_mid = (q.sale_lower_price + q.sale_upper_price) / 2 if q.sale_lower_price and q.sale_upper_price else None
        gap_ratio_sale = None
        if rtech_sale_mid and molit_sale_avg:
            gap_ratio_sale = round((rtech_sale_mid - molit_sale_avg) / molit_sale_avg * 100, 1)

        items.append(
            {
                "priv_area": q.priv_area,
                "pyong": q.pyong,
                "rtech_base_date": q.base_date,
                "rtech_sale_lower_price": q.sale_lower_price,
                "rtech_sale_upper_price": q.sale_upper_price,
                "rtech_jeonse_lower_price": q.jeonse_lower_price,
                "rtech_jeonse_upper_price": q.jeonse_upper_price,
                "molit_sale_avg_price": molit_sale_avg,
                "molit_sale_count": molit_sale_count,
                "molit_jeonse_avg_price": molit_jeonse_avg,
                "molit_jeonse_count": molit_jeonse_count,
                "gap_ratio_sale_pct": gap_ratio_sale,
            }
        )

    real_transactions = (
        db.query(RtechRealTransaction)
        .filter(RtechRealTransaction.rtech_complex_id == rtech_complex.id)
        .order_by(RtechRealTransaction.deal_ymd.desc())
        .limit(20)
        .all()
    )

    return {
        "complex_name": rtech_complex.apt_name,
        "sigungu": target_sigungu,
        "address": rtech_complex.address,
        "household_count": rtech_complex.household_count,
        "items": items,
        "rtech_real_transactions": [
            {
                "trade_mode": t.trade_mode,
                "deal_ymd": t.deal_ymd,
                "deal_amount": t.deal_amount,
                "area": t.area,
            }
            for t in real_transactions
        ],
    }
