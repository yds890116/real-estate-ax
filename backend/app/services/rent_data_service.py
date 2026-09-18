"""국토교통부 아파트 전월세 실거래가 원본 데이터를 정제해 rent_transactions에 적재한다.

매매 자료(dealAmount 등)와 달리 전월세 자료의 deposit/monthlyRent는 이미 만원 단위로
내려오므로 별도 환산이 필요 없다.
"""

from sqlalchemy.orm import Session

from app.models.rent_transaction import RentTransaction


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


def clean_rent_row(raw: dict[str, str], sido: str, sigungu: str) -> dict | None:
    deposit = _to_int(raw.get("deposit"))
    monthly_rent = _to_int(raw.get("monthlyRent")) or 0
    exclusive_area = _to_float(raw.get("excluUseAr"))
    year, month, day = raw.get("dealYear"), raw.get("dealMonth"), raw.get("dealDay")

    if deposit is None or exclusive_area is None or not (year and month and day):
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
        "deposit": deposit,
        "monthly_rent": monthly_rent,
        "contract_type": "월세" if monthly_rent > 0 else "전세",
        "deal_date": deal_date,
    }


def upsert_rent_transaction(db: Session, row: dict) -> tuple[RentTransaction, bool]:
    """row를 rent_transactions에 추가한다. 이미 존재하면 기존 행을 반환한다 (커밋은 호출부 책임)."""

    duplicate = (
        db.query(RentTransaction)
        .filter_by(
            sigungu=row["sigungu"],
            complex_name=row["complex_name"],
            exclusive_area=row["exclusive_area"],
            floor=row["floor"],
            deposit=row["deposit"],
            monthly_rent=row["monthly_rent"],
            deal_date=row["deal_date"],
        )
        .first()
    )
    if duplicate is not None:
        return duplicate, False

    obj = RentTransaction(**row, source="molit_api")
    db.add(obj)
    db.flush()
    return obj, True
