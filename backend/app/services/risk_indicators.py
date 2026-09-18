"""리스크 스코어링 v2의 개별 지표 계산.

각 함수는 (원본값 설명 문자열, 0~100 정규화 점수(높을수록 고위험), method) 를 반환한다.
정규화는 도메인 기준값(threshold) 사이 선형보간으로 처리한다 — threshold는 부동산 실무에서
통상 쓰이는 값을 참고한 근사치이며, 실제 서비스 적용 전 조정이 필요할 수 있다.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.risk_config import (
    DEFAULT_AUCTION_PRICE_RATIO,
    DEFAULT_POPULATION_CHANGE_PCT,
    DEFAULT_REGULATION_ZONE,
    DEFAULT_UNSOLD_UNITS,
    DUMMY_AUCTION_PRICE_RATIO,
    DUMMY_POPULATION_CHANGE_PCT,
    DUMMY_UNSOLD_UNITS,
    REGULATION_ZONES,
)
from app.models.market_transaction import MarketTransaction
from app.models.rent_transaction import RentTransaction

IndicatorResult = tuple[str, float, str]  # (description, normalized_score, method)


def _linear(value: float, low: float, high: float) -> float:
    """value<=low -> 0점, value>=high -> 100점 (low>high면 반대방향), 사이는 선형보간."""
    if high == low:
        return 50.0
    score = (value - low) / (high - low) * 100
    return max(0.0, min(100.0, score))


def _months_ago(months: int) -> str:
    return (date.today() - timedelta(days=months * 31)).isoformat()


# ── 1. 가격변동성 ──────────────────────────────────────────────────────────


def price_volatility_cv(db: Session, sigungu: str, months: int = 12) -> IndicatorResult:
    """최근 N개월 실거래 단가의 변동계수(CV=표준편차/평균*100). 낮을수록 안정적."""

    rows = (
        db.query(MarketTransaction)
        .filter(MarketTransaction.sigungu == sigungu, MarketTransaction.deal_date >= _months_ago(months))
        .all()
    )
    if len(rows) < 3:
        return f"최근 {months}개월 실거래 표본 부족({len(rows)}건)으로 중립값 적용", 40.0, "rule"

    prices = [r.deal_price / r.exclusive_area for r in rows]
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    cv_pct = (variance**0.5 / mean * 100) if mean else 0.0

    score = _linear(cv_pct, low=3.0, high=20.0)
    return f"최근 {months}개월 변동계수 {cv_pct:.1f}% ({len(rows)}건)", score, "ml"


def jeonse_ratio(db: Session, sigungu: str, months: int = 3) -> IndicatorResult:
    """전세가율(전세단가/매매단가). 높을수록 매매가 거품이 적어 안전하다고 본다."""

    cutoff = _months_ago(months)
    sale_rows = (
        db.query(MarketTransaction)
        .filter(MarketTransaction.sigungu == sigungu, MarketTransaction.deal_date >= cutoff)
        .all()
    )
    rent_rows = (
        db.query(RentTransaction)
        .filter(
            RentTransaction.sigungu == sigungu,
            RentTransaction.contract_type == "전세",
            RentTransaction.deal_date >= cutoff,
        )
        .all()
    )
    if len(sale_rows) < 2 or len(rent_rows) < 2:
        return "최근 매매·전세 표본 부족으로 중립값 적용", 40.0, "rule"

    sale_unit_price = sum(r.deal_price / r.exclusive_area for r in sale_rows) / len(sale_rows)
    jeonse_unit_price = sum(r.deposit / r.exclusive_area for r in rent_rows) / len(rent_rows)
    ratio_pct = (jeonse_unit_price / sale_unit_price * 100) if sale_unit_price else 0.0

    # 전세가율이 낮을수록(매매가와 갭이 클수록) 고위험 -> 역방향 선형보간
    score = _linear(ratio_pct, low=80.0, high=40.0)
    return f"전세가율 {ratio_pct:.1f}% (매매 {len(sale_rows)}건/전세 {len(rent_rows)}건)", score, "ml"


# ── 2. 유동성 ──────────────────────────────────────────────────────────────


def volume_change(db: Session, sigungu: str, months: int = 3) -> IndicatorResult:
    """최근 N개월 거래량과 그 이전 N개월 거래량의 증감률. 감소할수록 고위험."""

    recent_cutoff = _months_ago(months)
    prior_cutoff = _months_ago(months * 2)

    recent_count = (
        db.query(MarketTransaction)
        .filter(MarketTransaction.sigungu == sigungu, MarketTransaction.deal_date >= recent_cutoff)
        .count()
    )
    prior_count = (
        db.query(MarketTransaction)
        .filter(
            MarketTransaction.sigungu == sigungu,
            MarketTransaction.deal_date >= prior_cutoff,
            MarketTransaction.deal_date < recent_cutoff,
        )
        .count()
    )

    if prior_count < 3:
        return "이전 기간 거래표본 부족으로 중립값 적용", 40.0, "rule"

    change_pct = (recent_count - prior_count) / prior_count * 100
    score = _linear(-change_pct, low=-50.0, high=50.0)
    return f"최근 {months}개월 거래량 {recent_count}건, 이전 대비 {change_pct:+.0f}%", score, "ml"


def auction_price_ratio(sigungu: str) -> IndicatorResult:
    """낙찰가율 추이 — 공식 API가 없어 더미 데이터 사용(개발요건서 7절)."""

    ratio = DUMMY_AUCTION_PRICE_RATIO.get(sigungu, DEFAULT_AUCTION_PRICE_RATIO)
    score = _linear(ratio, low=100.0, high=70.0)
    return f"{sigungu} 낙찰가율 약 {ratio:.1f}% (더미 데이터)", score, "rule"


# ── 3. 지역공급 (샘플 데이터로 우선 구현) ──────────────────────────────────


def unsold_units(sigungu: str) -> IndicatorResult:
    units = DUMMY_UNSOLD_UNITS.get(sigungu, DEFAULT_UNSOLD_UNITS)
    score = _linear(units, low=0.0, high=300.0)
    return f"{sigungu} 미분양 약 {units}세대 (샘플 데이터)", score, "rule"


def population_change(sigungu: str) -> IndicatorResult:
    pct = DUMMY_POPULATION_CHANGE_PCT.get(sigungu, DEFAULT_POPULATION_CHANGE_PCT)
    score = _linear(-pct, low=-3.0, high=3.0)
    return f"{sigungu} 최근 1년 인구증감률 {pct:+.1f}% (샘플 데이터)", score, "rule"


# ── 4. 물건리스크 ──────────────────────────────────────────────────────────


def building_age(build_year: int | None) -> IndicatorResult:
    if build_year is None:
        return "준공연도 정보 없음으로 중립값 적용", 40.0, "rule"

    age = max(0, date.today().year - build_year)
    score = _linear(age, low=0.0, high=40.0)
    return f"준공 {age}년 경과", score, "rule"


def mortgage_ratio(mortgage_total: int | None, estimated_price: int | None) -> IndicatorResult:
    if not mortgage_total or not estimated_price:
        return "등기부등본 미확인으로 중립값 적용", 40.0, "rule"

    ratio_pct = mortgage_total / estimated_price * 100
    score = _linear(ratio_pct, low=0.0, high=100.0)
    return f"근저당 합계 {mortgage_total:,}만원 / AI 추정시세 {ratio_pct:.0f}%", score, "rule"


# ── 5. 정책리스크 ──────────────────────────────────────────────────────────


def regulation_zone(sigungu: str) -> IndicatorResult:
    zone_name, ltv_limit = REGULATION_ZONES.get(sigungu, DEFAULT_REGULATION_ZONE)
    # LTV 한도가 낮을수록(규제가 강할수록) 대출 실행 제약 리스크가 높다고 본다.
    score = _linear(70 - ltv_limit, low=0.0, high=30.0)
    return f"{sigungu} {zone_name} (LTV 한도 {ltv_limit}%, 더미 데이터)", score, "rule"
