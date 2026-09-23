from datetime import datetime

from pydantic import BaseModel


class CollateralScore(BaseModel):
    score: float
    grade: int
    grade_label: str
    method: str  # "ml" | "rule"
    observed_uscbd_cnt: int


class OnbidAuctionItemResponse(BaseModel):
    id: int
    cltr_mnmt_no: str
    plnm_no: str | None
    pbct_no: str | None
    cltr_nm: str | None
    ctgr_full_nm: str | None
    ldnm_adrs: str | None
    nmrd_adrs: str | None
    dpsl_mtd_nm: str | None
    bid_mtd_nm: str | None
    min_bid_prc: int | None
    apsl_ases_avg_amt: int | None
    fee_rate: str | None
    pbct_begn_dtm: str | None
    pbct_cls_dtm: str | None
    pbct_cltr_stat_nm: str | None
    uscbd_cnt: int | None
    appraisal_amt: int | None
    appraisal_date: str | None
    appraisal_org_nm: str | None
    collected_at: datetime
    score: CollateralScore | None = None

    class Config:
        from_attributes = True


class DailyCollectionSummary(BaseModel):
    collected_date: str  # YYYY-MM-DD
    item_count: int


class DailyItemsResponse(BaseModel):
    date: str
    items: list[OnbidAuctionItemResponse]
