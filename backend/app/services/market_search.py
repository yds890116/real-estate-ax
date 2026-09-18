"""주소/단지명 검색 → 카카오로 위치·법정동코드 해석 → 국토부 매매+전월세 실거래가 조회 →
단지명(또는 지번) 텍스트로 필터링해 해당 물건의 실거래가만 반환한다. 조회된 거래는
market_transactions/rent_transactions에도 적재해 이후 다른 기능이 함께 활용할 수 있게 한다.
"""

import re
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.market_data import MarketTransactionResponse, RentTransactionResponse
from app.schemas.market_search import LocationResolved, MarketSearchResult, RentSearchGroup, SaleSearchGroup
from app.services.external.kakao_client import resolve_location
from app.services.external.molit_client import MolitApiError, fetch_apt_rent_rows, fetch_apt_trade_rows
from app.services.market_data_service import clean_transaction_row, upsert_transaction
from app.services.rent_data_service import clean_rent_row, upsert_rent_transaction

DEFAULT_MONTHS = 3
MAX_MONTHS = 6


def _shift_month_str(base: date, months_back: int) -> str:
    month_index = base.month - 1 - months_back
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    return f"{year:04d}{month:02d}"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def name_matches(filter_text: str, candidate: str | None) -> bool:
    """두 단지명을 공백 제거 후 서로 부분포함 관계인지로 비교한다 (다른 서비스에서도 재사용)."""

    if not candidate:
        return False
    f, c = _normalize(filter_text), _normalize(candidate)
    return bool(f) and (f in c or c in f)


def _passes_filter(cleaned: dict, raw: dict, name_filter: str | None, jibun_filter: str | None) -> bool:
    if name_filter:
        return name_matches(name_filter, cleaned["complex_name"])
    if jibun_filter:
        return (raw.get("jibun") or "").strip() == jibun_filter
    # 필터가 전혀 없으면(형식 주소이지만 단지명/지번을 얻지 못한 경우) 해당 동의 전체 거래를 반환한다.
    return True


def search_market_transactions(db: Session, query: str, months: int = DEFAULT_MONTHS) -> MarketSearchResult:
    months = max(1, min(months, MAX_MONTHS))
    location = resolve_location(query)

    # 키워드(단지명) 검색이었으면 place_name을, 주소검색인데 건물명을 얻었으면 그것을 필터로 쓴다.
    name_filter = location.complex_name_hint or (query if location.source == "keyword" else None)
    jibun_filter = location.jibun
    filter_applied = name_filter or (f"지번 {jibun_filter}" if jibun_filter else None)

    months_searched: list[str] = []
    sale_fetched = 0
    rent_fetched = 0
    sale_rows = []
    rent_rows = []
    today = date.today()

    for i in range(months):
        ymd = _shift_month_str(today, i)
        months_searched.append(ymd)

        try:
            raw_sale_rows = fetch_apt_trade_rows(location.lawd_cd, ymd)
        except MolitApiError:
            raw_sale_rows = []
        sale_fetched += len(raw_sale_rows)

        for raw in raw_sale_rows:
            cleaned = clean_transaction_row(raw, location.sido, location.sigungu)
            if cleaned is None or not _passes_filter(cleaned, raw, name_filter, jibun_filter):
                continue
            obj, _ = upsert_transaction(db, cleaned)
            sale_rows.append(obj)

        try:
            raw_rent_rows = fetch_apt_rent_rows(location.lawd_cd, ymd)
        except MolitApiError:
            raw_rent_rows = []
        rent_fetched += len(raw_rent_rows)

        for raw in raw_rent_rows:
            cleaned = clean_rent_row(raw, location.sido, location.sigungu)
            if cleaned is None or not _passes_filter(cleaned, raw, name_filter, jibun_filter):
                continue
            obj, _ = upsert_rent_transaction(db, cleaned)
            rent_rows.append(obj)

    db.commit()
    for obj in [*sale_rows, *rent_rows]:
        db.refresh(obj)

    sale_transactions = [MarketTransactionResponse.model_validate(o) for o in sale_rows]
    sale_transactions.sort(key=lambda t: t.deal_date, reverse=True)

    rent_transactions = [RentTransactionResponse.model_validate(o) for o in rent_rows]
    rent_transactions.sort(key=lambda t: t.deal_date, reverse=True)

    return MarketSearchResult(
        location=LocationResolved(
            query=location.query,
            sido=location.sido,
            sigungu=location.sigungu,
            dong=location.dong,
            lawd_cd=location.lawd_cd,
            jibun=location.jibun,
            complex_name_hint=location.complex_name_hint,
            source=location.source,
        ),
        months_searched=months_searched,
        filter_applied=filter_applied,
        sale=SaleSearchGroup(total_fetched=sale_fetched, total_matched=len(sale_transactions), transactions=sale_transactions),
        rent=RentSearchGroup(total_fetched=rent_fetched, total_matched=len(rent_transactions), transactions=rent_transactions),
    )
