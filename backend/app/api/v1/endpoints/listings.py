from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.listing import ListingScrapeRequest, ListingScrapeResponse
from app.services.listing_service import scrape_and_store

router = APIRouter()


@router.post("/scrape", response_model=ListingScrapeResponse)
def scrape_listings(payload: ListingScrapeRequest, db: Session = Depends(get_db)):
    """Playwright 헤드리스 브라우저로 네이버 부동산 실시간 매물 수집을 시도한다.

    요청 사이 2~3초 지연을 두며(과도한 요청 방지), 네이버가 차단하면(현재 이 서버 환경에서는
    fin.land.naver.com API가 첫 요청부터 429를 반환해 거의 항상 차단된다) 샘플 데이터로
    자동 폴백한다. 어느 쪽이든 결과는 naver_listings 테이블에 저장된다."""

    return scrape_and_store(
        db,
        payload.complex_name,
        payload.sigungu,
        payload.reference_area,
        payload.reference_unit_price,
    )
