"""아파트/빌라 외 자산유형(오피스텔/상가/단독주택 등)의 원가법·수익환원법 참고 추정.

실거래가 비교사례 기반 추정(valuation_engine.py)이 마땅치 않은 자산유형을 위한 규칙 기반
근사치다. 단가·환원율은 자산유형별 참고 가정치(더미)이며, 실제 통계 기반 보정은 향후 과제.
"""

from app.schemas.cost_income import CostIncomeEstimate
from app.schemas.property import PropertyBase

# 자산유형별 가정치 (만원/㎡, 만원/㎡/월, 환원율). 공식 통계 연동 전까지의 참고 더미값.
ASSUMPTIONS: dict[str, dict[str, float]] = {
    "오피스텔": {"replacement_cost_per_area": 350, "unit_rent_per_area": 1.3, "cap_rate": 0.045},
    "상가": {"replacement_cost_per_area": 450, "unit_rent_per_area": 2.5, "cap_rate": 0.05},
    "단독주택": {"replacement_cost_per_area": 250, "unit_rent_per_area": 0.8, "cap_rate": 0.04},
    "토지": {"replacement_cost_per_area": 200, "unit_rent_per_area": 0.3, "cap_rate": 0.035},
}
DEFAULT_ASSUMPTION = {"replacement_cost_per_area": 300, "unit_rent_per_area": 1.0, "cap_rate": 0.045}

ANNUAL_DEPRECIATION_RATE = 0.02  # 정액법 연 감가율
MAX_DEPRECIATION_RATE = 0.6  # 최대 감가율(잔가율 하한 40%)
VACANCY_RATE = 0.05
OPEX_RATIO = 0.35
CONFIDENCE_LEVEL = 0.4  # 비교사례 기반 추정보다 낮게 고정 (가정치 기반 근사이므로)


def estimate_cost_income(prop: PropertyBase, current_year: int = 2026) -> CostIncomeEstimate:
    assumption = ASSUMPTIONS.get(prop.property_type, DEFAULT_ASSUMPTION)

    # 원가법
    age = max(0, current_year - prop.build_year) if prop.build_year else 0
    depreciation_rate = min(age * ANNUAL_DEPRECIATION_RATE, MAX_DEPRECIATION_RATE)
    replacement_cost_per_area = round(assumption["replacement_cost_per_area"])
    cost_approach_price = round(replacement_cost_per_area * (1 - depreciation_rate) * prop.exclusive_area)

    # 수익환원법
    unit_rent_per_area = assumption["unit_rent_per_area"]
    monthly_rent = unit_rent_per_area * prop.exclusive_area
    potential_gross_income = monthly_rent * 12
    effective_gross_income = potential_gross_income * (1 - VACANCY_RATE)
    annual_noi = round(effective_gross_income * (1 - OPEX_RATIO))
    cap_rate = assumption["cap_rate"]
    income_approach_price = round(annual_noi / cap_rate) if cap_rate else 0

    estimated_price = round((cost_approach_price + income_approach_price) / 2)
    price_per_area = round(estimated_price / prop.exclusive_area) if prop.exclusive_area else 0

    return CostIncomeEstimate(
        property_type=prop.property_type,
        replacement_cost_per_area=replacement_cost_per_area,
        depreciation_rate_pct=round(depreciation_rate * 100, 1),
        cost_approach_price=cost_approach_price,
        unit_rent_per_area=unit_rent_per_area,
        vacancy_rate_pct=round(VACANCY_RATE * 100, 1),
        opex_ratio_pct=round(OPEX_RATIO * 100, 1),
        cap_rate_pct=round(cap_rate * 100, 1),
        annual_noi=annual_noi,
        income_approach_price=income_approach_price,
        estimated_price=estimated_price,
        price_per_area=price_per_area,
        confidence_level=CONFIDENCE_LEVEL,
    )
