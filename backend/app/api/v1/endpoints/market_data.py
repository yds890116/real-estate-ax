from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.market_transaction import MarketTransaction
from app.schemas.market_data import (
    MarketTransactionResponse,
    TransactionIngestRequest,
    TransactionIngestResult,
)
from app.schemas.market_search import MarketSearchResult
from app.services.external.kakao_client import KakaoApiError
from app.services.external.lawd_codes import LawdCodeNotFoundError
from app.services.external.molit_client import MolitApiError
from app.services.market_data_service import ingest_apt_transactions
from app.services.market_search import DEFAULT_MONTHS, search_market_transactions

router = APIRouter()


@router.post("/ingest", response_model=TransactionIngestResult)
def ingest_transactions(payload: TransactionIngestRequest, db: Session = Depends(get_db)):
    """국토교통부 아파트 매매 실거래가 상세자료를 조회해 market_transactions에 정제·적재한다."""

    try:
        result = ingest_apt_transactions(db, payload.sido, payload.sigungu, payload.deal_ymd)
    except LawdCodeNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MolitApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return TransactionIngestResult(
        sido=payload.sido,
        sigungu=payload.sigungu,
        deal_ymd=payload.deal_ymd,
        **result,
    )


@router.get("/transactions", response_model=list[MarketTransactionResponse])
def list_transactions(
    sido: str | None = None,
    sigungu: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(MarketTransaction)
    if sido:
        query = query.filter(MarketTransaction.sido == sido)
    if sigungu:
        query = query.filter(MarketTransaction.sigungu == sigungu)
    return query.order_by(MarketTransaction.deal_date.desc()).limit(limit).all()


@router.get("/search", response_model=MarketSearchResult)
def search_transactions(
    query: str,
    months: int = DEFAULT_MONTHS,
    db: Session = Depends(get_db),
):
    """주소 또는 아파트 단지명으로 검색해 실제 실거래가를 조회한다.

    카카오 주소/키워드 검색 API로 입력을 법정동코드·좌표로 변환한 뒤, 국토교통부 실거래가
    API를 최근 `months`개월(기본 3, 최대 6) 조회해 단지명(또는 지번)으로 필터링한다.
    """

    try:
        return search_market_transactions(db, query, months=months)
    except KakaoApiError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MolitApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
