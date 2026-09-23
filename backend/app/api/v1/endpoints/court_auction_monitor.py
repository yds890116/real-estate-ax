from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.court_auction_item import CourtAuctionItem
from app.schemas.batch import CollectionRunResult
from app.schemas.court_auction import CourtAuctionDailyCollectionSummary, CourtAuctionDailyItemsResponse
from app.services.batch_collection_service import collect_court_auction_items

router = APIRouter()


@router.post("/collect", response_model=CollectionRunResult)
def collect_now(db: Session = Depends(get_db)):
    """법원경매정보에서 오늘 매각기일 기준 신규 매각공고 물건을 즉시 1회 수집한다 (테스트/데모용 수동 트리거)."""

    return collect_court_auction_items(db)


@router.get("/collection-dates", response_model=list[CourtAuctionDailyCollectionSummary])
def list_collection_dates(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    date_expr = func.date(CourtAuctionItem.collected_at)
    rows = (
        db.query(date_expr.label("collected_date"), func.count(CourtAuctionItem.id).label("item_count"))
        .filter(CourtAuctionItem.collected_at >= since)
        .group_by(date_expr)
        .order_by(date_expr.desc())
        .all()
    )
    return [CourtAuctionDailyCollectionSummary(collected_date=str(r.collected_date), item_count=r.item_count) for r in rows]


@router.get("/daily-items", response_model=CourtAuctionDailyItemsResponse)
def get_daily_items(target_date: str | None = None, db: Session = Depends(get_db)):
    target = target_date or datetime.utcnow().date().isoformat()
    date_expr = func.date(CourtAuctionItem.collected_at)
    items = (
        db.query(CourtAuctionItem)
        .filter(date_expr == target)
        .order_by(CourtAuctionItem.collected_at.desc())
        .all()
    )
    return CourtAuctionDailyItemsResponse(date=target, items=items)
