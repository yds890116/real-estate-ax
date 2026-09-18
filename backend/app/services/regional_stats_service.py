"""온비드 지역별 입찰 통계 수집·조회 서비스.

listing_service.py와 동일한 "실제 API 우선 시도 → 실패 시 샘플로 폴백" 구조를 따른다.
dedup 키는 (sido, sigungu, period, stats_type_cd) 조합이다.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.regional_bid_stat import RegionalBidStat
from app.services.external.onbid_stats_client import OnbidStatsApiError, fetch_regional_bid_stats
from app.services.regional_stats_sample import SIDO_LIST, get_all_sample_regional_stats


def _to_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def upsert_regional_stat(db: Session, row: dict) -> tuple[RegionalBidStat, bool]:
    """row를 regional_bid_stats에 저장한다. (저장된 행, 신규 여부) 반환. 커밋은 호출부 책임."""

    duplicate = (
        db.query(RegionalBidStat)
        .filter_by(
            sido=row["sido"],
            sigungu=row.get("sigungu"),
            period=row["period"],
            stats_type_cd=row.get("stats_type_cd"),
        )
        .first()
    )
    if duplicate is not None:
        return duplicate, False

    obj = RegionalBidStat(**row)
    db.add(obj)
    db.flush()
    return obj, True


def _period_type_of(period: str) -> str:
    if "-" in period:
        return "quarter"
    if len(period) == 6:
        return "month"
    return "year"


def collect_onbid_regional_stats(db: Session, inq_perd: str, stats_type_cd: str | None = None) -> dict:
    """실제 온비드 지역별 입찰 통계 API를 호출해 적재하고 실행 로그를 남긴다.

    서비스/오퍼레이션명이 미확정이라 현재는 항상 OnbidStatsApiError로 실패하지만 (자세한 사유는
    onbid_stats_client.py 참고), 실제 값이 확정되면 코드 수정 없이 바로 동작한다.
    """

    log = BatchRunLog(job_name="onbid_regional_stats", status="running")
    db.add(log)
    db.flush()

    collected = skipped = failed = 0
    error_message = None

    try:
        raw_rows = fetch_regional_bid_stats(inq_perd, stats_type_cd=stats_type_cd)
    except OnbidStatsApiError as e:
        log.collected_count = 0
        log.skipped_count = 0
        log.fail_count = 1
        log.error_message = str(e)
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"collected": 0, "skipped": 0, "failed": 1, "status": "failed", "error": str(e)}

    for raw in raw_rows:
        try:
            sido = (raw.get("SIDO_NM") or raw.get("ADDR1") or "").strip()
            if not sido:
                failed += 1
                continue
            row = {
                "sido": sido,
                "sigungu": (raw.get("SIGUNGU_NM") or raw.get("ADDR2") or "").strip() or None,
                "period": inq_perd,
                "period_type": _period_type_of(inq_perd),
                "stats_type_cd": stats_type_cd,
                "bid_count": _to_int(raw.get("PBCT_CNT")),
                "win_count": _to_int(raw.get("SSCBID_CNT")),
                "win_rate": _to_float(raw.get("SSCBID_RATE")),
                "avg_appraisal_amt": _to_int(raw.get("AVG_APSL_ASES_AMT")),
                "avg_min_bid_amt": _to_int(raw.get("AVG_MIN_BID_PRC")),
                "avg_win_bid_amt": _to_int(raw.get("AVG_SSCBID_AMT")),
                "avg_bid_rate_vs_appraisal": _to_float(raw.get("AVG_ASES_FEE_RATE")),
                "avg_bid_rate_vs_min_bid": _to_float(raw.get("AVG_MIN_BID_FEE_RATE")),
                "bidder_count": _to_int(raw.get("BIDR_CNT")),
                "competition_rate": _to_float(raw.get("CMPT_RATE")),
                "source": "onbid_stats_api",
            }
            _, was_new = upsert_regional_stat(db, row)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1
        except Exception as e:
            failed += 1
            error_message = str(e)

    db.commit()
    log.collected_count = collected
    log.skipped_count = skipped
    log.fail_count = failed
    log.error_message = error_message
    log.status = "failed" if (collected == 0 and skipped == 0 and failed) else ("partial_failure" if failed else "success")
    log.finished_at = datetime.now(timezone.utc)
    db.commit()

    return {"collected": collected, "skipped": skipped, "failed": failed, "status": log.status, "error": error_message}


def ensure_sample_data(db: Session) -> int:
    """regional_bid_stats에 실제 수집분이 전혀 없을 때만 샘플 데이터를 채운다. 채운 건수를 반환."""

    has_any = db.query(RegionalBidStat.id).first() is not None
    if has_any:
        return 0

    inserted = 0
    for row in get_all_sample_regional_stats():
        _, was_new = upsert_regional_stat(db, row)
        inserted += 1 if was_new else 0
    db.commit()
    return inserted


def get_region_list(db: Session) -> list[str]:
    ensure_sample_data(db)
    rows = db.query(RegionalBidStat.sido).distinct().order_by(RegionalBidStat.sido).all()
    return [r[0] for r in rows] or SIDO_LIST


def get_regional_trend(db: Session, sido: str, sigungu: str | None = None) -> tuple[list[RegionalBidStat], str, bool]:
    """sido(옵션 sigungu)의 기간별 통계를 오래된 순으로 반환. (행 목록, source, is_sample_data)."""

    ensure_sample_data(db)

    query = db.query(RegionalBidStat).filter(RegionalBidStat.sido == sido)
    query = query.filter(RegionalBidStat.sigungu == sigungu) if sigungu else query.filter(RegionalBidStat.sigungu.is_(None))
    rows = query.order_by(RegionalBidStat.period.asc()).all()

    source = rows[0].source if rows else "sample"
    return rows, source, source == "sample"


def get_regional_summary(db: Session, sido: str, sigungu: str | None = None) -> tuple[RegionalBidStat | None, str, bool]:
    """종합분석 화면 요약 카드용 - 가장 최근 1건. (최근 행, source, is_sample_data)."""

    ensure_sample_data(db)

    query = db.query(RegionalBidStat).filter(RegionalBidStat.sido == sido)
    query = query.filter(RegionalBidStat.sigungu == sigungu) if sigungu else query.filter(RegionalBidStat.sigungu.is_(None))
    latest = query.order_by(RegionalBidStat.period.desc()).first()

    source = latest.source if latest else "sample"
    return latest, source, source == "sample"
