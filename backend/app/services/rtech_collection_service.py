"""부동산테크(rtech.or.kr) 단지정보·시세·실거래가 수집 서비스.

지역(시도→구군→동) 순회 → 동별 단지 목록 조회 → 단지별 상세(기본정보/시세/실거래가) 수집
순서로 동작한다. 요청 사이 지연(2~3초)은 app/services/external/rtech_client.py에 중앙화돼 있어
이 서비스에서 별도로 sleep을 넣지 않아도 모든 HTTP 호출에 자동 적용된다.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.rtech_complex import RtechComplex
from app.models.rtech_price_quote import RtechPriceQuote
from app.models.rtech_real_transaction import RtechRealTransaction
from app.services.external.rtech_client import (
    RtechApiError,
    fetch_apt_area_price_list,
    fetch_apt_info,
    fetch_apt_list,
    fetch_apt_pyong_type_list,
    fetch_dong_list,
    fetch_market_price_base_date_list,
    fetch_real_price_monthly_list,
)


def _to_int(value) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        # API가 "                30,000"처럼 콤마·공백 포함 문자열로 숫자를 내려줄 때가 있다
        # (getMarketPriceAptAreaList.do의 S_LOWER_PRICE 등에서 실측 확인).
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def dong_code_to_reg_eub(dong_code: str) -> tuple[str, str]:
    """10자리 법정동코드를 getAptList.do가 요구하는 (reg_code, eub_code)로 변환한다.

    reg_code = 앞 5자리(시군구), eub_code = 그다음 3자리(읍면동, 말미 00 제외). 라이브 캡처로 확인됨
    (예: "1111012600" → reg_code="11110", eub_code="126").
    """
    return dong_code[:5], dong_code[5:8]


def upsert_complex(db: Session, raw: dict) -> tuple[RtechComplex | None, bool]:
    apt_seq = raw.get("SEQ")
    if apt_seq is None:
        return None, False

    existing = db.query(RtechComplex).filter_by(rtech_apt_seq=apt_seq).first()
    if existing is not None:
        return existing, False

    obj = RtechComplex(
        rtech_apt_seq=apt_seq,
        apt_name=(raw.get("APT_NAME") or "").strip(),
        addr_code=raw.get("ADDRCD"),
        household_count=_to_int(raw.get("KTECH_H_NUM")),
        dong_count=_to_int(raw.get("KTECH_TOT_DONG")),
        x_coord=raw.get("X"),
        y_coord=raw.get("Y"),
    )
    db.add(obj)
    db.flush()
    return obj, True


def enrich_complex_detail(db: Session, complex_obj: RtechComplex) -> None:
    """getMarketPriceAptInfo.do로 단지 기본정보(주소/세대수/준공월 등)를 채운다."""
    try:
        info = fetch_apt_info(complex_obj.rtech_apt_seq)
    except RtechApiError:
        return
    if not isinstance(info, dict) or not info:
        return

    complex_obj.sido = info.get("SIDO") or complex_obj.sido
    complex_obj.sigungu = info.get("SIGUNGU") or complex_obj.sigungu
    complex_obj.dong = info.get("DONG") or complex_obj.dong
    complex_obj.address = info.get("JUSO") or complex_obj.address
    complex_obj.road_address = info.get("NJUSO") or complex_obj.road_address
    complex_obj.household_count = _to_int(info.get("APT_H_NUM")) or complex_obj.household_count
    complex_obj.dong_count = info.get("APT_TOT_DONG") or complex_obj.dong_count
    complex_obj.min_floor = info.get("MIN_FLOOR")
    complex_obj.max_floor = info.get("MAX_FLOOR")
    complex_obj.use_approval_ym = info.get("USEAPR_YM")
    complex_obj.area_range = info.get("PRIV_AREA_AROUND")
    db.flush()


def upsert_price_quote(db: Session, complex_obj: RtechComplex, raw: dict, base_date: str) -> tuple[RtechPriceQuote | None, bool]:
    priv_area = raw.get("PRIV_AREA")
    if priv_area is None:
        return None, False

    existing = (
        db.query(RtechPriceQuote)
        .filter_by(rtech_complex_id=complex_obj.id, priv_area=priv_area, base_date=base_date)
        .first()
    )
    if existing is not None:
        return existing, False

    obj = RtechPriceQuote(
        rtech_complex_id=complex_obj.id,
        pyong_seq=raw.get("KTECH_PYONG_SEQ"),
        pyong=raw.get("PYONG"),
        priv_area=priv_area,
        base_date=base_date,
        sale_lower_price=_to_int(raw.get("S_LOWER_PRICE")),
        sale_upper_price=_to_int(raw.get("S_UPPER_PRICE")),
        jeonse_lower_price=_to_int(raw.get("R_LOWER_PRICE")),
        jeonse_upper_price=_to_int(raw.get("R_UPPER_PRICE")),
        household_count=_to_int(raw.get("HOUSE_CNT")),
    )
    db.add(obj)
    db.flush()
    return obj, True


def upsert_real_transaction(db: Session, complex_obj: RtechComplex, raw: dict) -> tuple[RtechRealTransaction | None, bool]:
    deal_ymd = raw.get("M_DEAL_YMD")
    deal_amount = _to_int(raw.get("M_DEAL_AMT"))
    area = raw.get("BLDG_AREA")
    trade_mode = raw.get("TRADE_MODE")
    if not deal_ymd or deal_amount is None or area is None or not trade_mode:
        return None, False

    existing = (
        db.query(RtechRealTransaction)
        .filter_by(rtech_complex_id=complex_obj.id, deal_ymd=deal_ymd, area=area, deal_amount=deal_amount, trade_mode=trade_mode)
        .first()
    )
    if existing is not None:
        return existing, False

    obj = RtechRealTransaction(
        rtech_complex_id=complex_obj.id,
        trade_mode=trade_mode,
        deal_ymd=deal_ymd,
        deal_amount=deal_amount,
        area=area,
    )
    db.add(obj)
    db.flush()
    return obj, True


def _collect_complex_detail(db: Session, complex_obj: RtechComplex, base_date: str) -> dict:
    """단지 1곳의 기본정보/시세/실거래가를 모두 수집한다. 개별 API 실패는 다른 단지 수집을 막지 않는다."""

    collected = skipped = failed = 0

    enrich_complex_detail(db, complex_obj)

    try:
        price_rows = fetch_apt_area_price_list(complex_obj.rtech_apt_seq, base_date)
    except RtechApiError:
        price_rows = []
        failed += 1

    for raw in price_rows:
        _, was_new = upsert_price_quote(db, complex_obj, raw, base_date)
        collected += 1 if was_new else 0
        skipped += 0 if was_new else 1

    try:
        pyong_rows = fetch_apt_pyong_type_list(complex_obj.rtech_apt_seq)
    except RtechApiError:
        pyong_rows = []
        failed += 1

    deal_ym = base_date.replace("-", "")[:6]
    for pyong_row in pyong_rows:
        pyong = pyong_row.get("PYONG")
        if pyong is None:
            continue
        try:
            txn_rows = fetch_real_price_monthly_list(complex_obj.rtech_apt_seq, pyong, deal_ym)
        except RtechApiError:
            failed += 1
            continue
        for raw in txn_rows:
            _, was_new = upsert_real_transaction(db, complex_obj, raw)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1

    return {"collected": collected, "skipped": skipped, "failed": failed}


def collect_dong(db: Session, do_code: str, city_code: str, dong_code: str, dong_name: str = "") -> dict:
    """동 1곳의 단지 목록을 조회하고, 각 단지의 기본정보·시세·실거래가를 모두 수집한다."""

    job_name = "rtech_collect"
    log = BatchRunLog(job_name=job_name, status="running")
    db.add(log)
    db.flush()

    collected = skipped = failed = 0
    error_messages: list[str] = []

    try:
        base_dates = fetch_market_price_base_date_list()
        base_date = base_dates[0]["AMT_DT"] if base_dates else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        reg_code, eub_code = dong_code_to_reg_eub(dong_code)
        apt_rows = fetch_apt_list(reg_code, eub_code)
    except RtechApiError as e:
        log.collected_count = 0
        log.skipped_count = 0
        log.fail_count = 1
        log.error_message = str(e)
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"dong_name": dong_name, "complex_count": 0, "collected": 0, "skipped": 0, "failed": 1, "status": "failed", "error": str(e)}

    complex_count = 0
    for raw in apt_rows:
        try:
            complex_obj, _ = upsert_complex(db, raw)
            if complex_obj is None:
                continue
            complex_count += 1
            detail_result = _collect_complex_detail(db, complex_obj, base_date)
            collected += detail_result["collected"]
            skipped += detail_result["skipped"]
            failed += detail_result["failed"]
            db.commit()
        except Exception as e:  # 단지 1곳의 오류가 나머지 단지 수집을 막지 않는다
            failed += 1
            error_messages.append(str(e))
            db.rollback()

    error_message = "; ".join(error_messages) or None
    log.collected_count = collected
    log.skipped_count = skipped
    log.fail_count = failed
    log.error_message = error_message
    log.status = "failed" if (collected == 0 and skipped == 0 and failed) else ("partial_failure" if failed else "success")
    log.finished_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "dong_name": dong_name,
        "complex_count": complex_count,
        "collected": collected,
        "skipped": skipped,
        "failed": failed,
        "status": log.status,
        "error": error_message,
    }


def collect_sigungu(db: Session, do_code: str, city_code: str) -> list[dict]:
    """구/군 1곳의 전체 동을 순회하며 collect_dong을 반복 호출한다."""

    dong_rows = fetch_dong_list(do_code, city_code)
    return [collect_dong(db, do_code, city_code, row["DONG_CODE"], row.get("DONG_NAME", "")) for row in dong_rows]
