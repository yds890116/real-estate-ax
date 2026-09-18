from pydantic import BaseModel


class TransactionIngestRequest(BaseModel):
    sido: str
    sigungu: str
    deal_ymd: str  # YYYYMM


class TransactionIngestResult(BaseModel):
    sido: str
    sigungu: str
    deal_ymd: str
    fetched: int
    cleaned: int
    inserted: int
    skipped_duplicate: int


class MarketTransactionResponse(BaseModel):
    id: int
    sido: str
    sigungu: str
    dong: str | None
    complex_name: str | None
    exclusive_area: float
    floor: int | None
    build_year: int | None
    deal_price: int
    deal_date: str
    source: str

    class Config:
        from_attributes = True


class RentTransactionResponse(BaseModel):
    id: int
    sido: str
    sigungu: str
    dong: str | None
    complex_name: str | None
    exclusive_area: float
    floor: int | None
    build_year: int | None
    deposit: int  # 만원
    monthly_rent: int  # 만원 (0이면 전세)
    contract_type: str  # "전세" | "월세"
    deal_date: str
    source: str

    class Config:
        from_attributes = True
