from datetime import datetime

from pydantic import BaseModel


class CourtAuctionItemResponse(BaseModel):
    id: int
    docid: str
    case_no: str
    item_no: str | None
    court_name: str | None
    dept_name: str | None
    usage_name: str | None
    address: str | None
    building_detail: str | None
    remarks: str | None
    appraisal_amt: int | None
    min_sale_price: int | None
    min_sale_price_rate: str | None
    failed_count: int | None
    sale_date: str | None
    status: str | None
    collected_at: datetime

    class Config:
        from_attributes = True


class CourtAuctionDailyCollectionSummary(BaseModel):
    collected_date: str  # YYYY-MM-DD
    item_count: int


class CourtAuctionDailyItemsResponse(BaseModel):
    date: str
    items: list[CourtAuctionItemResponse]
