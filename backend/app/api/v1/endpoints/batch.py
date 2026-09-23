from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.batch_run_log import BatchRunLog
from app.schemas.batch import BatchRunLogResponse, DailyCollectionRunResult
from app.services.batch_collection_service import collect_court_auction_items, collect_naver_news, collect_onbid_auction_items

router = APIRouter()


@router.post("/run", response_model=DailyCollectionRunResult)
def run_collection_now(db: Session = Depends(get_db)):
    """온비드 공매/법원경매/네이버 뉴스 수집 배치를 즉시 1회 실행한다 (테스트/데모용 수동 트리거).

    매일 새벽 자동 실행되는 스케줄과 동일한 로직을 사용하며, 실행 결과는 batch_run_logs에 기록된다.
    """

    onbid_result = collect_onbid_auction_items(db)
    court_auction_result = collect_court_auction_items(db)
    news_result = collect_naver_news(db)
    return DailyCollectionRunResult(onbid_auction=onbid_result, court_auction=court_auction_result, naver_news=news_result)


@router.get("/logs", response_model=list[BatchRunLogResponse])
def list_batch_logs(job_name: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    """배치 실행 로그(수집 건수/중복 건수/실패 건수)를 최신순으로 조회한다."""

    query = db.query(BatchRunLog)
    if job_name:
        query = query.filter(BatchRunLog.job_name == job_name)
    return query.order_by(BatchRunLog.started_at.desc()).limit(limit).all()
