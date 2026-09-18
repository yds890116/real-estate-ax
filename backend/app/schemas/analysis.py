from pydantic import BaseModel

from app.schemas.appraisal import AppraisalSearchResult
from app.schemas.listing import ListingComparison, ListingSearchResult
from app.schemas.property import PropertyResponse
from app.schemas.registry import RegistryAnalysisResult
from app.schemas.risk import RiskScoreResult
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
