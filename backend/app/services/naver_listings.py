"""네이버 부동산 매물 샘플 데이터 생성기.

실제 수집은 app/services/naver_scraper.py(Playwright 헤드리스 브라우저)가 담당한다.
이 모듈은 그 스크래핑이 차단됐을 때(이 서버 환경에서는 fin.land.naver.com API가 첫
요청부터 429 Too Many Requests를 반환해 거의 항상 차단된다 — naver_scraper.py 상단
docstring 참고)의 폴백이다. CLAUDE.md의 "공식 API가 없는 데이터는 초기엔 샘플/더미
데이터로 화면과 로직부터 구현" 원칙에 따른 것이다.

참고 단가(같은 단지 실거래가 기반)를 기준으로 현실적인 범위의 매물을 생성해 화면 로직/
레이아웃과 괴리율 계산 로직을 실제 데이터 없이도 검증할 수 있게 한다.
"""

import hashlib
import random

from app.schemas.listing import SAMPLE_NOTICE, ListingItem, ListingSearchResult

REALTORS = ["대치공인중개사", "강남더샵부동산", "한강뷰공인중개사", "래미안부동산", "탑공인중개사"]
DEFAULT_UNIT_PRICE = 4000  # 만원/㎡, 참고 단가가 없을 때의 기본값
TRADE_TYPE_POOL = ["매매", "매매", "전세", "월세"]
LISTING_COUNT = 5


def get_sample_listings(complex_name: str, reference_area: float, reference_unit_price: int | None) -> ListingSearchResult:
    # 단지명 기반 시드를 써서 새로고침해도 매번 같은 매물 목록이 나오게 한다 (진짜 데이터처럼 안정적으로 보이게).
    seed = int(hashlib.sha1(complex_name.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    base_unit_price = reference_unit_price or DEFAULT_UNIT_PRICE

    listings: list[ListingItem] = []
    for i in range(LISTING_COUNT):
        trade_type = rng.choice(TRADE_TYPE_POOL)
        area = round(reference_area + rng.uniform(-0.5, 0.5), 2)
        floor = rng.randint(2, 25)
        unit_price = round(base_unit_price * rng.uniform(0.92, 1.08))
        sale_equivalent_price = round(unit_price * area)

        monthly_rent = None
        if trade_type == "매매":
            price = sale_equivalent_price
        elif trade_type == "전세":
            price = round(sale_equivalent_price * rng.uniform(0.55, 0.75))
        else:  # 월세
            price = round(sale_equivalent_price * rng.uniform(0.1, 0.25))
            monthly_rent = round(sale_equivalent_price * rng.uniform(0.002, 0.004))

        listings.append(
            ListingItem(
                id=f"sample-{complex_name}-{i + 1}",
                complex_name=complex_name,
                exclusive_area=area,
                floor=f"{floor}층",
                trade_type=trade_type,
                price=price,
                monthly_rent=monthly_rent,
                realtor=rng.choice(REALTORS),
            )
        )

    listings.sort(key=lambda item: item.exclusive_area)

    return ListingSearchResult(
        complex_name=complex_name,
        reference_area=reference_area,
        listings=listings,
        source="sample",
        is_sample_data=True,
        notice=SAMPLE_NOTICE,
    )
