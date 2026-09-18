from pydantic import BaseModel

SAMPLE_NOTICE = (
    "네이버 부동산 실시간 수집이 차단되어(429 Too Many Requests) 참고용 샘플 매물을 표시합니다. "
    "실제 매물 정보는 네이버 부동산에서 직접 확인해주세요."
)
LIVE_NOTICE = "Playwright로 네이버 부동산에서 실시간 수집한 매물입니다."


class ListingItem(BaseModel):
    id: str
    complex_name: str
    exclusive_area: float
    floor: str
    trade_type: str  # "매매" | "전세" | "월세"
    price: int  # 만원 (매매가 또는 보증금)
    monthly_rent: int | None = None  # 만원, 월세일 때만
    realtor: str | None = None
    source: str = "sample"  # "naver_scrape" | "sample"


class ListingSearchResult(BaseModel):
    complex_name: str
    reference_area: float
    listings: list[ListingItem]
    source: str = "sample"  # "naver_scrape" | "sample"
    is_sample_data: bool = True
    notice: str = SAMPLE_NOTICE


class ListingScrapeRequest(BaseModel):
    complex_name: str
    sigungu: str | None = None
    reference_area: float | None = None  # 샘플 폴백 시 기준 평형 (없으면 84.97㎡ 기본값)
    reference_unit_price: int | None = None  # 샘플 폴백 시 기준 단가(만원/㎡, 없으면 기본값)


class ListingScrapeResponse(BaseModel):
    complex_name: str
    source: str  # "naver_scrape" | "sample"
    blocked: bool
    block_reason: str | None
    listings: list[ListingItem]


class ListingComparison(BaseModel):
    reference_area: float
    market_unit_price: int | None  # 만원/㎡, 최근 실거래 평균
    listing_unit_price: int | None  # 만원/㎡, 매물 호가 평균 (매매만)
    gap_ratio: float | None  # (매물단가-실거래단가)/실거래단가 * 100 (%)
    listing_count: int
    market_transaction_count: int
    explanation: str
