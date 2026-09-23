from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.onbid_auction_item import OnbidAuctionItem
from app.schemas.onbid_monitor import CollateralScore, DailyCollectionSummary, DailyItemsResponse, OnbidAuctionItemResponse
from app.services.collateral_scoring_service import score_item

router = APIRouter()


@router.get("/collection-dates", response_model=list[DailyCollectionSummary])
def list_collection_dates(days: int = 30, db: Session = Depends(get_db)):
    """최근 수집이 있었던 날짜별 신규 물건 건수 - 일자별 매물 목록 화면의 날짜 선택용."""

    since = datetime.utcnow() - timedelta(days=days)
    date_expr = func.date(OnbidAuctionItem.collected_at)
    rows = (
        db.query(date_expr.label("collected_date"), func.count(OnbidAuctionItem.id).label("item_count"))
        .filter(OnbidAuctionItem.collected_at >= since)
        .group_by(date_expr)
        .order_by(date_expr.desc())
        .all()
    )
    return [DailyCollectionSummary(collected_date=str(r.collected_date), item_count=r.item_count) for r in rows]


@router.get("/daily-items", response_model=DailyItemsResponse)
def get_daily_items(target_date: str | None = None, db: Session = Depends(get_db)):
    """target_date(YYYY-MM-DD, 기본 오늘)에 신규 수집된 온비드 공매 물건 목록."""

    target = target_date or date.today().isoformat()
    date_expr = func.date(OnbidAuctionItem.collected_at)
    items = (
        db.query(OnbidAuctionItem)
        .filter(date_expr == target)
        .order_by(OnbidAuctionItem.collected_at.desc())
        .all()
    )
    responses = []
    for i in items:
        item_resp = OnbidAuctionItemResponse.model_validate(i)
        item_resp.score = CollateralScore(**score_item(i))
        responses.append(item_resp)
    return DailyItemsResponse(date=target, items=responses)
