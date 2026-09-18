"""국토교통부 실거래가 원본 데이터를 정제해 market_transactions 테이블에 적재한다."""

from sqlalchemy.orm import Session

from app.models.market_transaction import MarketTransaction
from app.services.external.lawd_codes import get_lawd_cd
from app.services.external.molit_client import fetch_apt_trade_rows


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.replace(",", "").strip())
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def clean_transaction_row(raw: dict[str, str], sido: str, sigungu: str) -> dict | None:
    # 국토부 실거래가 상세자료 API는 영문 필드명을 사용한다 (dealAmount, excluUseAr 등).
    cancel_type = (raw.get("cdealType") or "").strip()
    if cancel_type:  # 계약 해제(취소)된 거래는 제외
        return None

    deal_price = _to_int(raw.get("dealAmount"))
    exclusive_area = _to_float(raw.get("excluUseAr"))
    year, month, day = raw.get("dealYear"), raw.get("dealMonth"), raw.get("dealDay")

    if deal_price is None or exclusive_area is None or not (year and month and day):
        return None

    try:
        deal_date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return None

    return {
        "sido": sido,
        "sigungu": sigungu,
        "dong": (raw.get("umdNm") or "").strip() or None,
        "complex_name": (raw.get("aptNm") or "").strip() or None,
        "exclusive_area": exclusive_area,
        "floor": _to_int(raw.get("floor")),
        "build_year": _to_int(raw.get("buildYear")),
        "deal_price": deal_price,
        "deal_date": deal_date,
    }


def upsert_transaction(db: Session, row: dict) -> tuple[MarketTransaction, bool]:
    """row를 market_transactions에 추가한다. 이미 존재하면 기존 행을 반환한다 (커밋은 호출부 책임).

    반환값은 (영속화된 행, 새로 추가됐는지 여부). 새로 추가한 경우 flush로 id를 확보해둔다.
    """

    duplicate = (
        db.query(MarketTransaction)
        .filter_by(
            sigungu=row["sigungu"],
            complex_name=row["complex_name"],
            exclusive_area=row["exclusive_area"],
            floor=row["floor"],
            deal_price=row["deal_price"],
            deal_date=row["deal_date"],
        )
        .first()
    )
    if duplicate is not None:
        return duplicate, False

    obj = MarketTransaction(**row, source="molit_api")
    db.add(obj)
    db.flush()
    return obj, True


def ingest_apt_transactions(db: Session, sido: str, sigungu: str, deal_ymd: str) -> dict[str, int]:
    """sido/sigungu 지역의 deal_ymd(YYYYMM) 아파트 매매 실거래가를 수집·정제·적재한다."""

    lawd_cd = get_lawd_cd(sido, sigungu)
    raw_rows = fetch_apt_trade_rows(lawd_cd, deal_ymd)

    cleaned_rows = [row for row in (clean_transaction_row(r, sido, sigungu) for r in raw_rows) if row is not None]

    inserted = 0
    for row in cleaned_rows:
        _, was_new = upsert_transaction(db, row)
        inserted += was_new
    db.commit()

    return {
        "fetched": len(raw_rows),
        "cleaned": len(cleaned_rows),
        "inserted": inserted,
        "skipped_duplicate": len(cleaned_rows) - inserted,
    }
