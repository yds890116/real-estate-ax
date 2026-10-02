from pydantic import BaseModel

from app.schemas.appraisal import AppraisalSearchResult
from app.schemas.cost_income import CostIncomeEstimate
from app.schemas.land_valuation import LandValuationResult
from app.schemas.listing import ListingComparison, ListingSearchResult
from app.schemas.property import PropertyResponse
from app.schemas.registry import RegistryAnalysisResult
from app.schemas.risk import RiskScoreResult
from app.schemas.rone_index import RegionTrendFeatures
from app.schemas.valuation import ValuationResult


class PropertyAnalysis(BaseModel):
    """종합분석 화면에 필요한 시세+리스크+권리분석+유사감정사례 통합 응답."""

    property: PropertyResponse
    valuation: ValuationResult
    risk: RiskScoreResult
    registry: RegistryAnalysisResult | None = None  # 등기부등본을 업로드한 경우에만 존재
    appraisal: AppraisalSearchResult  # 유사 거래·감정평가 사례 검색 결과 (매 조회시 자동 계산)
    listings: ListingSearchResult | None = None  # 네이버 부동산 매물 (현재 샘플 데이터, complex_name 있을 때만)
    listing_comparison: ListingComparison | None = None  # 실거래가 vs 매물호가 괴리율
    regional_trend: RegionTrendFeatures | None = None  # R-ONE 지역 통계(가격동향/실거래가격지수/지가변동률/임대동향)
    cost_income_estimate: CostIncomeEstimate | None = None  # 아파트/빌라 외 자산유형에만 존재(원가법·수익환원법)
    land_valuation: LandValuationResult | None = None  # 토지 특성·개발잠재력·입지가치 종합 평가
