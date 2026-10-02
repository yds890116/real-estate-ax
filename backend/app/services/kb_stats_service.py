"""KB부동산 데이터허브 주택가격동향조사(매매/전세/월세 가격지수) 수집·조회 서비스.

PublicDataReader의 Kbland가 시/도 단위(전국 포함 25개 지역) 월간 지수를 API 키 없이 제공한다.
월세는 KB가 전월대비 증감률 API를 따로 주지 않아(아파트 월세가격지수만 제공) 저장된 지수값으로
직접 전월대비 증감률을 계산해 채운다. dedup 키는 (region_cd, trade_type, period) 조합이다.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.regional_kb_price_index import RegionalKbPriceIndex
from app.services.external.kb_land_client import (
    KbLandApiError,
    TRADE_JEONSE,
    TRADE_SALE,
    TRADE_TYPE_LABELS,
    fetch_monthly_wolse_index,
    fetch_price_index,
    fetch_price_index_change_rate,
)
from app.services.rone_index_service import SIDO_SHORT_NAME

TREND_CHART_MONTHS = 24


def _start_log(db: Session, job_name: str) -> BatchRunLog:
    log = BatchRunLog(job_name=job_name, status="running")
    db.add(log)
    db.flush()
    return log


def _finish_log(db: Session, log: BatchRunLog, collected: int, skipped: int, failed: int, error_message: str | None = None) -> None:
    log.collected_count = collected
    log.skipped_count = skipped
    log.fail_count = failed
    log.error_message = error_message
    log.status = "failed" if error_message and collected == 0 and skipped == 0 else ("partial_failure" if failed else "success")
    log.finished_at = datetime.now(timezone.utc)
    db.commit()


def _merge_index_and_rate(index_rows: list[dict], rate_rows: list[dict]) -> dict[tuple, dict]:
    """(지역코드, 날짜) 키로 가격지수와 증감률 원본 행을 하나로 병합한다."""
    merged: dict[tuple, dict] = {}
    for row in index_rows:
        key = (row.get("지역코드"), row.get("날짜"))
        merged.setdefault(key, {}).update(row)
    for row in rate_rows:
        key = (row.get("지역코드"), row.get("날짜"))
        entry = merged.setdefault(key, {})
        entry.update({k: v for k, v in row.items() if k != "가격지수"})  # 가격지수는 index_rows 값을 우선 유지
        entry["가격지수증감률"] = row.get("가격지수증감률")
    return merged


def upsert_kb_price_index(db: Session, row: dict) -> tuple[RegionalKbPriceIndex | None, bool]:
    """raw(병합된) 행 1건을 regional_kb_price_indices에 저장한다. (저장된 행, 신규 여부) 반환."""

    region_cd = row.get("지역코드")
    period = row.get("날짜")
    trade_type = row.get("거래구분")
    if not region_cd or not period or not trade_type:
        return None, False

    duplicate = db.query(RegionalKbPriceIndex).filter_by(region_cd=region_cd, trade_type=trade_type, period=period).first()
    if duplicate is not None:
        return duplicate, False

    obj = RegionalKbPriceIndex(
        region_cd=region_cd,
        region_name=row.get("지역명") or "",
        housing_type=row.get("매물종별구분") or "",
        trade_type=trade_type,
        period=period,
        index_value=row.get("가격지수"),
        change_rate=row.get("가격지수증감률"),
    )
    db.add(obj)
    db.flush()
    return obj, True


def _collect_trade_type(db: Session, trade_type_code: str) -> dict:
    label = TRADE_TYPE_LABELS[trade_type_code]
    job_name = f"kb_price_index_{label}"
    log = _start_log(db, job_name)
    collected = skipped = failed = 0
    error_message: str | None = None

    try:
        index_rows = fetch_price_index(trade_type_code)
        rate_rows = fetch_price_index_change_rate(trade_type_code)
    except KbLandApiError as e:
        _finish_log(db, log, 0, 0, 1, str(e))
        return {"job_name": job_name, "collected": 0, "skipped": 0, "failed": 1, "status": "failed", "error": str(e)}

    merged = _merge_index_and_rate(index_rows, rate_rows)
    for row in merged.values():
        try:
            _, was_new = upsert_kb_price_index(db, row)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1
        except Exception as e:  # 항목 단위 오류는 배치 전체를 중단시키지 않는다
            failed += 1
            error_message = str(e)

    db.commit()
    _finish_log(db, log, collected, skipped, failed, error_message)
    return {"job_name": job_name, "collected": collected, "skipped": skipped, "failed": failed, "status": log.status, "error": error_message}


def _collect_wolse(db: Session) -> dict:
    job_name = "kb_price_index_월세"
    log = _start_log(db, job_name)
    collected = skipped = failed = 0
    error_message: str | None = None

    try:
        rows = fetch_monthly_wolse_index()
    except KbLandApiError as e:
        _finish_log(db, log, 0, 0, 1, str(e))
        return {"job_name": job_name, "collected": 0, "skipped": 0, "failed": 1, "status": "failed", "error": str(e)}

    # KB가 월세 증감률 API를 따로 주지 않아, 지역별로 날짜순 정렬 후 전월 대비 증감률을 직접 계산한다.
    by_region: dict[str, list[dict]] = {}
    for row in rows:
        by_region.setdefault(row.get("지역코드"), []).append(row)

    for region_rows in by_region.values():
        region_rows.sort(key=lambda r: r["날짜"])
        prev_value: float | None = None
        for row in region_rows:
            value = row.get("가격지수")
            row["가격지수증감률"] = round((value - prev_value) / prev_value * 100, 4) if prev_value and value is not None else None
            if value is not None:
                prev_value = value
            try:
                _, was_new = upsert_kb_price_index(db, row)
                collected += 1 if was_new else 0
                skipped += 0 if was_new else 1
            except Exception as e:
                failed += 1
                error_message = str(e)

    db.commit()
    _finish_log(db, log, collected, skipped, failed, error_message)
    return {"job_name": job_name, "collected": collected, "skipped": skipped, "failed": failed, "status": log.status, "error": error_message}


def collect_kb_price_indices(db: Session) -> list[dict]:
    """매매/전세/월세 가격지수를 모두 수집한다. 하나가 실패해도 나머지는 계속 수집한다."""

    return [
        _collect_trade_type(db, TRADE_SALE),
        _collect_trade_type(db, TRADE_JEONSE),
        _collect_wolse(db),
    ]


def get_kb_price_trend(db: Session, sido: str, months: int = TREND_CHART_MONTHS) -> dict:
    """시도 단위 KB 매매/전세/월세 가격지수 최근 N개월 시계열을 반환한다.

    테이블이 완전히 비어 있으면(최초 요청) 즉시 라이브로 한 번 채운다 - 이 API는 키가 필요 없고
    응답도 수 초 내로 빨라(온비드처럼 네트워크가 막혀 있지 않은 한) 첫 요청에서 바로 채워진다.
    """

    has_any = db.query(RegionalKbPriceIndex.id).first() is not None
    if not has_any:
        collect_kb_price_indices(db)

    short_sido = SIDO_SHORT_NAME.get(sido, sido)

    rows = db.query(RegionalKbPriceIndex).filter(RegionalKbPriceIndex.region_name == short_sido).all()
    region_matched = short_sido if rows else None
    if not rows:
        rows = db.query(RegionalKbPriceIndex).filter(RegionalKbPriceIndex.region_name == "전국").all()
        region_matched = "전국" if rows else None

    region_cd = rows[0].region_cd if rows else None

    by_period: dict[str, dict] = {}
    for r in rows:
        entry = by_period.setdefault(r.period, {"period": r.period})
        if r.trade_type == "매매":
            entry["sale_index"] = r.index_value
            entry["sale_change_rate"] = r.change_rate
        elif r.trade_type == "전세":
            entry["jeonse_index"] = r.index_value
            entry["jeonse_change_rate"] = r.change_rate
        elif r.trade_type == "월세":
            entry["wolse_index"] = r.index_value
            entry["wolse_change_rate"] = r.change_rate

    recent_periods = sorted(by_period.keys())[-months:]
    points = [by_period[p] for p in recent_periods]

    return {
        "sido": sido,
        "region_matched": region_matched,
        "region_cd": region_cd,
        "points": points,
        "notice": "KB부동산 데이터허브 주택가격동향조사(주택종합 기준) 통계이며, 월세지수는 수도권(서울·경기·인천) 등 일부 지역만 제공됩니다.",
    }
