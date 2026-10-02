from pydantic import BaseModel


class LandCharacteristics(BaseModel):
    pnu: str | None = None
    jimok: str | None = None  # 지목
    land_use_zone: str | None = None  # 용도지역
    land_use_district: str | None = None  # 용도지구
    official_land_price: int | None = None  # 개별공시지가(원/㎡)
    official_land_price_base_date: str | None = None  # 공시기준일 (YYYY-MM)
    address: str | None = None
    available: bool
    notice: str


class DevelopmentPotential(BaseModel):
    legal_bcr_cap_pct: float | None = None  # 법정 건폐율 상한(%)
    legal_far_cap_pct: float | None = None  # 법정 용적률 상한(%)
    current_floors: int | None = None  # 현재 건축물 층수(추정)
    implied_max_floors: float | None = None  # 법정 상한 기준 추정 최대 층수(용적률/건폐율)
    utilization_ratio_pct: float | None = None  # 현재 층수 / 추정 최대 층수 (%)
    development_potential_index: float | None = None  # 0~100, 높을수록 개발잠재력(여지) 큼
    notice: str


class LocationValue(BaseModel):
    nearest_subway_name: str | None = None
    nearest_subway_distance_m: float | None = None
    road_type: str | None = None  # "대로" | "로" | "길" 등 (도로명 어미 기반 근사)
    location_value_score: float | None = None  # 0~100
    notice: str


class LandValuationResult(BaseModel):
    characteristics: LandCharacteristics
    development_potential: DevelopmentPotential
    location_value: LocationValue
    land_price_change_pct: float | None = None  # R-ONE 지가변동률(최신, %)
    land_trade_price_per_sqm: float | None = None  # 국토부 토지 실거래가 최근 평균(원/㎡)
    land_valuation_score: float | None = None  # 종합 토지가치평가점수 0~100 (리스크 엔진 반영용)
    disclaimer: str
