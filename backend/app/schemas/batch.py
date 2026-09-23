from datetime import datetime

from pydantic import BaseModel


class CollectionRunResult(BaseModel):
    collected: int
    skipped: int
    failed: int
    status: str
    error: str | None = None
    appraisal_enriched: int = 0


class DailyCollectionRunResult(BaseModel):
    onbid_auction: CollectionRunResult
    court_auction: CollectionRunResult
    naver_news: CollectionRunResult


class BatchRunLogResponse(BaseModel):
    id: int
    job_name: str
    status: str
    collected_count: int
    skipped_count: int
    fail_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True
