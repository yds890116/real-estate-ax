from pydantic import BaseModel


class RoneTableIngestResult(BaseModel):
    job_name: str
    collected: int
    skipped: int
    failed: int
    status: str
    error: str | None = None


class RegionTrendFeatures(BaseModel):
    sido: str
    sigungu: str | None
    region_matched: str | None
    apt_actual_txn_sale_latest: float | None
    apt_actual_txn_sale_mom_change_pct: float | None
    apt_price_trend_sale_latest: float | None
    apt_price_trend_sale_mom_change_pct: float | None
    apt_price_trend_jeonse_latest: float | None
    apt_price_trend_jeonse_mom_change_pct: float | None
