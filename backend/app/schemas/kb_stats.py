from pydantic import BaseModel


class KbStatsIngestResult(BaseModel):
    job_name: str
    collected: int
    skipped: int
    failed: int
    status: str
    error: str | None = None


class KbPriceTrendPoint(BaseModel):
    period: str  # YYYY-MM
    sale_index: float | None = None
    jeonse_index: float | None = None
    wolse_index: float | None = None
    sale_change_rate: float | None = None
    jeonse_change_rate: float | None = None
    wolse_change_rate: float | None = None


class KbPriceTrendResponse(BaseModel):
    sido: str
    region_matched: str | None
    region_cd: str | None
    points: list[KbPriceTrendPoint]
    notice: str
