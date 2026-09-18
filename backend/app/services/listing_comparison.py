"""매물 호가(네이버 부동산)와 국토부 실거래가를 같은 단지·평형 기준으로 비교해
괴리율(%)을 계산한다 (요구사항 5)."""

from app.schemas.listing import ListingComparison, ListingItem

AREA_TOLERANCE_SQM = 3.0  # 같은 평형으로 볼 전용면적 오차범위(㎡, 매물은 실거래보다 표기가 들쑥날쑥해 실거래(1㎡)보다 넓게 잡음


def compare_to_market(
    listings: list[ListingItem],
    reference_area: float,
    market_unit_price: int | None,
    market_transaction_count: int,
) -> ListingComparison:
    tier_sale_listings = [
        item
        for item in listings
        if item.trade_type == "매매" and abs(item.exclusive_area - reference_area) <= AREA_TOLERANCE_SQM
    ]

    listing_unit_price = None
    if tier_sale_listings:
        unit_prices = [item.price / item.exclusive_area for item in tier_sale_listings]
        listing_unit_price = round(sum(unit_prices) / len(unit_prices))

    gap_ratio = None
    if listing_unit_price is not None and market_unit_price:
        gap_ratio = round((listing_unit_price - market_unit_price) / market_unit_price * 100, 1)

    if gap_ratio is None:
        explanation = "비교할 매매 매물 또는 실거래가가 부족해 괴리율을 계산하지 못했습니다."
    elif gap_ratio > 5:
        explanation = f"매물 호가가 최근 실거래가보다 평균 {gap_ratio}% 높습니다 — 매도자 희망가가 반영된 호가일 수 있어 유의가 필요합니다."
    elif gap_ratio < -5:
        explanation = f"매물 호가가 최근 실거래가보다 평균 {abs(gap_ratio)}% 낮습니다 — 급매물이거나 시세 하락 국면일 수 있습니다."
    else:
        explanation = f"매물 호가({gap_ratio:+.1f}%)가 최근 실거래가와 유사한 수준입니다."

    return ListingComparison(
        reference_area=reference_area,
        market_unit_price=market_unit_price,
        listing_unit_price=listing_unit_price,
        gap_ratio=gap_ratio,
        listing_count=len(tier_sale_listings),
        market_transaction_count=market_transaction_count,
        explanation=explanation,
    )
