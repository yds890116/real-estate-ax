from pydantic import BaseModel


class CostIncomeEstimate(BaseModel):
    """아파트/빌라 외 자산유형(오피스텔/상가/단독주택 등)의 원가법·수익환원법 참고 추정치.

    실거래가 비교사례가 부족한 자산유형에 대한 규칙 기반 근사치이며, 실제 감정평가(3방식 병용,
    토지가치 별도 산정 등)를 대체하지 않는다.
    """

    property_type: str

    # 원가법(Cost Approach)
    replacement_cost_per_area: int  # 만원/㎡, 유형별 표준 재조달원가 단가(가정치)
    depreciation_rate_pct: float  # 감가율(%) = 경과연수 × 연 감가율(정액법, 상한 적용)
    cost_approach_price: int  # 만원, 재조달원가 × (1-감가율) × 전용면적

    # 수익환원법(Income Capitalization Approach)
    unit_rent_per_area: float  # 만원/㎡/월, 유형별 표준 임대료 단가(가정치)
    vacancy_rate_pct: float
    opex_ratio_pct: float
    cap_rate_pct: float
    annual_noi: int  # 만원, 순영업소득
    income_approach_price: int  # 만원, NOI / 환원율

    estimated_price: int  # 만원, 두 접근법의 단순평균
    price_per_area: int  # 만원/㎡
    confidence_level: float  # 0~1, 비교사례 기반 추정보다 낮게 고정
    disclaimer: str = (
        "원가법·수익환원법 참고 추정치입니다(가정 단가·환원율 기반 근사치). "
        "토지가치는 별도 반영되지 않았으며, 실제 감정평가와 차이가 있을 수 있습니다."
    )
