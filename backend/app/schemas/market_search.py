from pydantic import BaseModel

from app.schemas.market_data import MarketTransactionResponse, RentTransactionResponse


class LocationResolved(BaseModel):
    query: str
    sido: str
    sigungu: str
    dong: str | None
    lawd_cd: str
    jibun: str | None
    complex_name_hint: str | None
    source: str  # "address" | "keyword"


class SaleSearchGroup(BaseModel):
    total_fetched: int
    total_matched: int
    transactions: list[MarketTransactionResponse]


class RentSearchGroup(BaseModel):
    total_fetched: int
    total_matched: int
    transactions: list[RentTransactionResponse]


class MarketSearchResult(BaseModel):
    location: LocationResolved
    months_searched: list[str]
    filter_applied: str | None  # 실제로 적용된 단지명/지번 필터 (없으면 null = 동 전체 반환)
    sale: SaleSearchGroup
    rent: RentSearchGroup
