"""한국부동산원 R-ONE 지역별 주택가격지수 수집·조회 서비스.

수집 대상 3개 통계표 (data.go.kr가 아닌 R-ONE 자체 도메인에서 실제 라이브 조회로 확인됨):
- A_2024_00176: (월) 지역별 매매지수_공동주택통합 → "공동주택 실거래가격지수"(신고 실거래 기반, 매매)
- A_2024_00045: (월) 매매가격지수_아파트 → 전국주택가격동향조사 매매가격지수(표본조사 기반)
- A_2024_00050: (월) 전세가격지수_아파트 → 전국주택가격동향조사 전세가격지수(표본조사 기반)

dedup 키는 (statbl_id, region_cd, period) 조합이다. 시세 추정 엔진(XGBoost)은 이미 학습된 고정
피처셋을 쓰므로, 이 모듈은 재학습 없이 바로 쓸 수 있는 "지역 트렌드 보조 지표" 조회 함수
(get_region_trend_features)까지만 제공한다 — 실제로 모델 피처에 편입하려면 학습 데이터셋에
이 지표를 포함해 app/ml/train.py를 재학습해야 한다.
"""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.regional_price_index import RegionalPriceIndex
from app.services.external.rone_client import RoneApiError, fetch_stats

TABLE_DEFS = [
    {
        "job_name": "rone_apt_actual_txn_sale",
        "statbl_id": "A_2024_00176",
        "index_type": "actual_transaction",
        "trade_type": "sale",
        "label": "공동주택 실거래가격지수(매매)",
    },
    {
        "job_name": "rone_apt_price_trend_sale",
        "statbl_id": "A_2024_00045",
        "index_type": "price_trend",
        "trade_type": "sale",
        "label": "아파트 매매가격지수",
    },
    {
        "job_name": "rone_apt_price_trend_jeonse",
        "statbl_id": "A_2024_00050",
        "index_type": "price_trend",
        "trade_type": "jeonse",
        "label": "아파트 전세가격지수",
    },
]

# R-ONE CLS_NM/CLS_FULLNM은 시도를 축약형으로 표기한다 (프로젝트 내 Property.sido는 정식 명칭 사용).
SIDO_SHORT_NAME = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


def _recent_period_range(months_back: int) -> tuple[str, str]:
    today = date.today()
    total_months = today.year * 12 + (today.month - 1) - (months_back - 1)
    start_year, start_month = divmod(total_months, 12)
    return f"{start_year:04d}{start_month + 1:02d}", today.strftime("%Y%m")


def upsert_price_index(db: Session, table_def: dict, raw: dict) -> tuple[RegionalPriceIndex | None, bool]:
    """raw row 1건을 regional_price_indices에 저장한다. (저장된 행, 신규 여부) 반환."""

    region_cd = raw.get("CLS_ID")
    period = raw.get("WRTTIME_IDTFR_ID")
    dta_val = raw.get("DTA_VAL")
    if region_cd is None or not period or dta_val is None:
        return None, False

    duplicate = (
        db.query(RegionalPriceIndex)
        .filter_by(statbl_id=table_def["statbl_id"], region_cd=region_cd, period=period)
        .first()
    )
    if duplicate is not None:
        return duplicate, False

    obj = RegionalPriceIndex(
        statbl_id=table_def["statbl_id"],
        index_type=table_def["index_type"],
        trade_type=table_def["trade_type"],
        period=period,
        region_cd=region_cd,
        region_name=raw.get("CLS_NM") or "",
        region_full_name=raw.get("CLS_FULLNM") or "",
        index_value=float(dta_val),
    )
    db.add(obj)
    db.flush()
    return obj, True


def _collect_one_table(db: Session, table_def: dict, months_back: int) -> dict:
    log = BatchRunLog(job_name=table_def["job_name"], status="running")
    db.add(log)
    db.flush()

    start_wrttime, end_wrttime = _recent_period_range(months_back)
    collected = skipped = failed = 0
    error_message = None

    try:
        raw_rows = fetch_stats(table_def["statbl_id"], "MM", start_wrttime, end_wrttime)
    except RoneApiError as e:
        log.collected_count = 0
        log.skipped_count = 0
        log.fail_count = 1
        log.error_message = str(e)
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"job_name": table_def["job_name"], "collected": 0, "skipped": 0, "failed": 1, "status": "failed", "error": str(e)}

    for raw in raw_rows:
        try:
            _, was_new = upsert_price_index(db, table_def, raw)
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

    return {
        "job_name": table_def["job_name"],
        "collected": collected,
        "skipped": skipped,
        "failed": failed,
        "status": log.status,
        "error": error_message,
    }


def collect_regional_price_indices(db: Session, months_back: int = 6) -> list[dict]:
    """3개 통계표를 모두 수집한다. 통계표별로 실행 로그를 남기며, 하나가 실패해도 나머지는 계속 수집한다."""

    return [_collect_one_table(db, table_def, months_back) for table_def in TABLE_DEFS]


def get_region_trend_features(db: Session, sido: str, sigungu: str | None = None) -> dict:
    """시세 추정 엔진 등에서 지역 트렌드 보조 피처로 쓸 수 있는 최신 지수·변동률 요약을 반환한다.

    시군구 단위로 먼저 매칭을 시도하고, 없으면 시도 단위로 폴백한다. "공동주택 실거래가격지수"
    (A_2024_00176)는 실제로 시군구가 아니라 수도권/지방/서울/경기/5대광역시 같은 광역 단위로만
    발표되는 것으로 라이브 조회에서 확인됐다 — 이 지표는 대부분의 경우 시도 단위 폴백으로만
    값이 채워진다. 나머지 두 지표(매매/전세가격지수_아파트)는 시군구 단위까지 제공된다.
    데이터가 없으면 값이 None인 채로 채워진 dict를 반환한다(호출부에서 결측 처리하기 쉽도록).
    """

    short_sido = SIDO_SHORT_NAME.get(sido, sido)

    result: dict = {"sido": sido, "sigungu": sigungu, "region_matched": None}

    for table_def in TABLE_DEFS:
        key = table_def["job_name"].removeprefix("rone_")

        rows = []
        for candidate in ([sigungu] if sigungu else []) + [short_sido]:
            rows = (
                db.query(RegionalPriceIndex)
                .filter(RegionalPriceIndex.statbl_id == table_def["statbl_id"], RegionalPriceIndex.region_name == candidate)
                .order_by(RegionalPriceIndex.period.desc())
                .limit(2)
                .all()
            )
            if rows:
                break

        if not rows:
            result[f"{key}_latest"] = None
            result[f"{key}_mom_change_pct"] = None
            continue

        result["region_matched"] = rows[0].region_full_name
        result[f"{key}_latest"] = rows[0].index_value
        if len(rows) == 2 and rows[1].index_value:
            result[f"{key}_mom_change_pct"] = round((rows[0].index_value - rows[1].index_value) / rows[1].index_value * 100, 2)
        else:
            result[f"{key}_mom_change_pct"] = None

    return result
