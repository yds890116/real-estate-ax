"""네이버 매물 수집 오케스트레이션 + 저장 (요구사항 4: DB 적재).

실제 스크래핑(naver_scraper)을 우선 시도하고, 차단되면 샘플 생성기(naver_listings)로
폴백한다. 두 경로 모두 결과를 naver_listings 테이블에 저장해(source 컬럼으로 구분) 이후
종합분석 화면 조회가 매번 스크래핑을 재시도하지 않고 저장된 스냅샷을 바로 쓸 수 있게 한다.
"""

from sqlalchemy.orm import Session

from app.models.naver_listing import NaverListing
from app.schemas.listing import LIVE_NOTICE, SAMPLE_NOTICE, ListingItem, ListingScrapeResponse, ListingSearchResult
from app.services.naver_listings import get_sample_listings
from app.services.naver_scraper import scrape_complex_listings

DEFAULT_REFERENCE_AREA = 84.97  # 국민평형, reference_area가 전혀 없을 때의 최후 기본값


def persist_listings(db: Session, complex_name: str, sigungu: str | None, items: list[ListingItem], source: str) -> None:
    # 매물은 특정 시점의 스냅샷이라 최신 수집분만 의미가 있다 — 같은 단지의 이전 수집분은 지운다.
    db.query(NaverListing).filter(NaverListing.complex_name == complex_name).delete()
    for item in items:
        db.add(
            NaverListing(
                complex_name=complex_name,
                sigungu=sigungu,
                exclusive_area=item.exclusive_area,
                floor=item.floor,
                trade_type=item.trade_type,
                price=item.price,
                monthly_rent=item.monthly_rent,
                realtor=item.realtor,
                listed_date=None,
                source=source,
            )
        )
    db.commit()


def scrape_and_store(
    db: Session,
    complex_name: str,
    sigungu: str | None,
    reference_area: float | None,
    reference_unit_price: int | None,
) -> ListingScrapeResponse:
    """실시간 스크래핑을 실제로 시도(Playwright, 요청 사이 2~3초 지연)하고 결과를 저장한다."""

    scrape_result = scrape_complex_listings(complex_name)

    if not scrape_result.blocked and scrape_result.listings:
        items = [
            ListingItem(
                id=f"naver-{complex_name}-{i}",
                complex_name=item.complex_name,
                exclusive_area=item.exclusive_area,
                floor=item.floor or "-",
                trade_type=item.trade_type,
                price=item.price,
                monthly_rent=item.monthly_rent,
                realtor=item.realtor,
                source="naver_scrape",
            )
            for i, item in enumerate(scrape_result.listings)
        ]
        source = "naver_scrape"
    else:
        sample = get_sample_listings(complex_name, reference_area or DEFAULT_REFERENCE_AREA, reference_unit_price)
        items = sample.listings
        source = "sample"

    persist_listings(db, complex_name, sigungu, items, source)

    return ListingScrapeResponse(
        complex_name=complex_name,
        source=source,
        blocked=scrape_result.blocked,
        block_reason=scrape_result.block_reason,
        listings=items,
    )


def get_cached_or_sample_listings(
    db: Session,
    complex_name: str,
    reference_area: float,
    reference_unit_price: int | None,
) -> ListingSearchResult:
    """종합분석 화면에서 매 조회 시 자동으로 쓰는 빠른 경로 — Playwright를 띄우지 않는다.

    이전에 /listings/scrape로 실제 수집을 트리거해 저장해둔 데이터가 있으면 그것을 쓰고,
    없으면 즉석에서 샘플 데이터를 생성한다. 실시간 스크래핑은 명시적으로 트리거할 때만
    실행한다(브라우저 구동 비용이 커 종합분석 조회마다 실행하기엔 부적합)."""

    cached = db.query(NaverListing).filter(NaverListing.complex_name == complex_name).all()
    if cached:
        source = cached[0].source
        items = [
            ListingItem(
                id=f"cached-{row.id}",
                complex_name=row.complex_name,
                exclusive_area=row.exclusive_area,
                floor=row.floor or "-",
                trade_type=row.trade_type,
                price=row.price,
                monthly_rent=row.monthly_rent,
                realtor=row.realtor,
                source=source,
            )
            for row in cached
        ]
        return ListingSearchResult(
            complex_name=complex_name,
            reference_area=reference_area,
            listings=items,
            source=source,
            is_sample_data=source == "sample",
            notice=LIVE_NOTICE if source == "naver_scrape" else SAMPLE_NOTICE,
        )

    return get_sample_listings(complex_name, reference_area, reference_unit_price)
