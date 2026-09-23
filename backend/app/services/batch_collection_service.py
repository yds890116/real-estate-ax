"""매일 새벽 자동 실행되는 데이터 수집 배치의 핵심 로직.

- 온비드 공매 물건·감정가 데이터 수집 (cltr_mnmt_no 물건관리번호 기준 중복 체크)
- 네이버 뉴스 검색 API로 부동산 정책 뉴스 수집 (link 기사 링크 기준 중복 체크)

각 수집 함수는 실행 1회당 batch_run_logs에 수집 건수/중복 건수/실패 건수를 기록한다.
개별 항목 처리 중 오류가 나도 전체 배치가 중단되지 않도록 항목 단위로 예외를 흡수한다.
"""

import html
import re
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.court_auction_item import CourtAuctionItem
from app.models.news_article import NewsArticle
from app.models.onbid_auction_item import OnbidAuctionItem
from app.services.external.court_auction_client import CourtAuctionBlockedError, fetch_new_listings
from app.services.external.naver_news_client import NaverNewsApiError, fetch_news_items
from app.services.external.onbid_client import OnbidApiError, fetch_appraisal_detail, fetch_public_sale_items

# 뉴스 수집에 사용할 검색어 목록 (부동산 정책 관련)
NEWS_SEARCH_KEYWORDS = ["부동산 정책", "주택 대출 규제", "부동산 세제 개편"]


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.replace(",", "").strip())
    except ValueError:
        return None


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


def upsert_onbid_item(db: Session, raw: dict[str, str], source: str = "onbid_api") -> tuple[OnbidAuctionItem | None, bool]:
    """raw 온비드 물건 행을 onbid_auction_items에 저장한다. (저장된 행, 신규 여부) 반환. 필수값 없으면 None 반환."""

    cltr_mnmt_no = (raw.get("CLTR_MNMT_NO") or "").strip()
    if not cltr_mnmt_no:
        return None, False

    duplicate = db.query(OnbidAuctionItem).filter_by(cltr_mnmt_no=cltr_mnmt_no).first()
    if duplicate is not None:
        return duplicate, False

    obj = OnbidAuctionItem(
        cltr_mnmt_no=cltr_mnmt_no,
        plnm_no=raw.get("PLNM_NO") or None,
        pbct_no=raw.get("PBCT_NO") or None,
        cltr_nm=raw.get("CLTR_NM") or None,
        ctgr_full_nm=raw.get("CTGR_FULL_NM") or None,
        ldnm_adrs=raw.get("LDNM_ADRS") or None,
        nmrd_adrs=raw.get("NMRD_ADRS") or None,
        dpsl_mtd_nm=raw.get("DPSL_MTD_NM") or None,
        bid_mtd_nm=raw.get("BID_MTD_NM") or None,
        min_bid_prc=_to_int(raw.get("MIN_BID_PRC")),
        apsl_ases_avg_amt=_to_int(raw.get("APSL_ASES_AVG_AMT")),
        fee_rate=raw.get("FEE_RATE") or None,
        pbct_begn_dtm=raw.get("PBCT_BEGN_DTM") or None,
        pbct_cls_dtm=raw.get("PBCT_CLS_DTM") or None,
        pbct_cltr_stat_nm=raw.get("PBCT_CLTR_STAT_NM") or None,
        uscbd_cnt=_to_int(raw.get("USCBD_CNT")),
        source=source,
    )
    if raw.get("_COLLECTED_AT") is not None:
        obj.collected_at = raw["_COLLECTED_AT"]
    db.add(obj)
    db.flush()
    return obj, True


def ensure_onbid_sample_data(db: Session) -> int:
    """onbid_auction_items가 완전히 비어 있을 때만(=실제 수집이 전혀 안 된 상태) 샘플 데이터를 채운다.

    스코어링 모델 학습·화면 검증을 위한 것으로, 실제 수집분이 하나라도 있으면 아무것도 하지 않는다."""

    from app.services.onbid_auction_sample import get_sample_onbid_items

    has_any = db.query(OnbidAuctionItem.id).first() is not None
    if has_any:
        return 0

    inserted = 0
    for raw in get_sample_onbid_items():
        _, was_new = upsert_onbid_item(db, raw, source="sample")
        inserted += 1 if was_new else 0
    db.commit()
    return inserted


def _enrich_appraisal_detail(db: Session, item: OnbidAuctionItem) -> bool:
    """신규 수집 물건 1건에 감정평가 기준정보(감정가/평가일자/평가업체)를 best-effort로 채운다.

    OnbidApiError(연결 실패 포함)는 조용히 무시한다 - 이 정보는 부가정보이며, 없다고 해서
    물건 자체의 수집을 실패로 만들지 않는다. 성공 시 True를 반환한다."""

    try:
        detail = fetch_appraisal_detail(item.cltr_mnmt_no)
    except OnbidApiError:
        return False
    if not detail:
        return False

    item.appraisal_amt = _to_int(detail.get("APSL_ASES_AMT"))
    item.appraisal_date = detail.get("APSL_ASES_DT") or None
    item.appraisal_org_nm = detail.get("APSL_ASES_ORG_NM") or None
    db.flush()
    return True


def collect_onbid_auction_items(db: Session, num_of_rows: int = 100, enrich_appraisal: bool = True) -> dict[str, int]:
    """온비드 공매 물건·감정가 데이터를 수집해 onbid_auction_items에 적재하고 실행 로그를 남긴다.

    신규로 수집된(이미 있던 물건이 아닌) 건에 한해 감정평가 기준정보도 함께 조회를 시도한다
    (enrich_appraisal=True 기본값) - 매번 전체를 다시 조회하지 않도록 신규 건만 대상으로 한다."""

    log = _start_log(db, "onbid_auction")
    collected = skipped = failed = 0
    appraisal_enriched = 0
    error_messages: list[str] = []

    try:
        raw_rows = fetch_public_sale_items(num_of_rows=num_of_rows)
    except OnbidApiError as e:
        _finish_log(db, log, collected=0, skipped=0, failed=1, error_message=str(e))
        return {"collected": 0, "skipped": 0, "failed": 1, "status": log.status, "error": str(e)}

    for raw in raw_rows:
        try:
            item, was_new = upsert_onbid_item(db, raw)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1
            if was_new and enrich_appraisal and item is not None:
                appraisal_enriched += 1 if _enrich_appraisal_detail(db, item) else 0
        except Exception as e:  # 항목 단위 오류는 배치 전체를 중단시키지 않는다
            failed += 1
            error_messages.append(str(e))

    db.commit()
    error_message = "; ".join(error_messages) or None
    _finish_log(db, log, collected=collected, skipped=skipped, failed=failed, error_message=error_message)
    return {
        "collected": collected,
        "skipped": skipped,
        "failed": failed,
        "appraisal_enriched": appraisal_enriched,
        "status": log.status,
        "error": error_message,
    }


def _clean_multiline(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _derive_court_auction_status(failed_count: int | None) -> str:
    if not failed_count:
        return "신건"
    return f"유찰 {failed_count}회"


def upsert_court_auction_item(db: Session, raw: dict) -> tuple[CourtAuctionItem | None, bool]:
    """raw 법원경매정보 물건상세검색 행을 court_auction_items에 저장한다. (저장된 행, 신규 여부) 반환."""

    docid = (raw.get("docid") or "").strip()
    case_no = (raw.get("srnSaNo") or "").strip()
    if not docid or not case_no:
        return None, False

    duplicate = db.query(CourtAuctionItem).filter_by(docid=docid).first()
    if duplicate is not None:
        return duplicate, False

    failed_count = _to_int(raw.get("yuchalCnt"))
    min_sale_price = _to_int(raw.get("notifyMinmaePrice1")) or _to_int(raw.get("minmaePrice"))

    obj = CourtAuctionItem(
        docid=docid,
        case_no=case_no,
        item_no=raw.get("mokmulSer") or None,
        court_name=raw.get("jiwonNm") or None,
        dept_name=raw.get("jpDeptNm") or None,
        usage_name=raw.get("dspslUsgNm") or None,
        address=_clean_multiline(raw.get("printSt")),
        building_detail=_clean_multiline(raw.get("pjbBuldList")),
        remarks=_clean_multiline(raw.get("mulBigo")),
        appraisal_amt=_to_int(raw.get("gamevalAmt")),
        min_sale_price=min_sale_price,
        min_sale_price_rate=raw.get("notifyMinmaePriceRate1") or None,
        failed_count=failed_count,
        sale_date=raw.get("maeGiil") or None,
        status=_derive_court_auction_status(failed_count),
    )
    db.add(obj)
    db.flush()
    return obj, True


def collect_court_auction_items(db: Session, target_date: date | None = None) -> dict[str, int]:
    """법원경매정보(courtauction.go.kr)에서 target_date(기본값 오늘) 매각기일 기준 전국 물건을
    수집해 court_auction_items에 적재하고 실행 로그를 남긴다."""

    log = _start_log(db, "court_auction")
    collected = skipped = failed = 0
    error_message: str | None = None

    try:
        raw_rows = fetch_new_listings(target_date or date.today())
    except CourtAuctionBlockedError as e:
        _finish_log(db, log, collected=0, skipped=0, failed=1, error_message=str(e))
        return {"collected": 0, "skipped": 0, "failed": 1, "status": log.status, "error": str(e)}

    for raw in raw_rows:
        try:
            _, was_new = upsert_court_auction_item(db, raw)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1
        except Exception as e:  # 항목 단위 오류는 배치 전체를 중단시키지 않는다
            failed += 1
            error_message = str(e)

    db.commit()
    _finish_log(db, log, collected=collected, skipped=skipped, failed=failed, error_message=error_message)
    return {"collected": collected, "skipped": skipped, "failed": failed, "status": log.status, "error": error_message}


def _clean_html(text: str) -> str:
    """네이버 검색 API 응답의 <b> 강조 태그와 &quot; 등 HTML 엔티티를 제거한다."""
    return html.unescape(re.sub(r"</?b>", "", text or "")).strip()


def upsert_news_article(db: Session, raw: dict, search_keyword: str) -> tuple[NewsArticle | None, bool]:
    """raw 네이버 뉴스 검색 결과 1건을 news_articles에 저장한다. (저장된 행, 신규 여부) 반환."""

    link = (raw.get("link") or "").strip()
    if not link:
        return None, False

    duplicate = db.query(NewsArticle).filter_by(link=link).first()
    if duplicate is not None:
        return duplicate, False

    obj = NewsArticle(
        link=link,
        original_link=raw.get("originallink") or None,
        title=_clean_html(raw.get("title", "")),
        description=_clean_html(raw.get("description", "")),
        pub_date=raw.get("pubDate") or None,
        search_keyword=search_keyword,
    )
    db.add(obj)
    db.flush()
    return obj, True


def collect_naver_news(db: Session, keywords: list[str] | None = None) -> dict[str, int]:
    """부동산 정책 관련 뉴스를 검색어별로 수집해 news_articles에 적재하고 실행 로그를 남긴다."""

    log = _start_log(db, "naver_news")
    collected = skipped = failed = 0
    error_messages: list[str] = []

    for keyword in keywords or NEWS_SEARCH_KEYWORDS:
        try:
            raw_items = fetch_news_items(keyword, display=100, sort="date")
        except NaverNewsApiError as e:
            failed += 1
            error_messages.append(f"[{keyword}] {e}")
            continue

        for raw in raw_items:
            try:
                _, was_new = upsert_news_article(db, raw, keyword)
                collected += 1 if was_new else 0
                skipped += 0 if was_new else 1
            except Exception as e:
                failed += 1
                error_messages.append(f"[{keyword}] {e}")

    db.commit()
    error_message = "; ".join(error_messages) or None
    _finish_log(db, log, collected=collected, skipped=skipped, failed=failed, error_message=error_message)
    return {"collected": collected, "skipped": skipped, "failed": failed, "status": log.status, "error": error_message}


def run_daily_collection_job() -> dict[str, dict[str, int]]:
    """APScheduler가 매일 새벽 호출하는 진입점. 요청 컨텍스트 밖이므로 자체 세션을 연다."""

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        onbid_result = collect_onbid_auction_items(db)
        court_auction_result = collect_court_auction_items(db)
        news_result = collect_naver_news(db)
        return {"onbid_auction": onbid_result, "court_auction": court_auction_result, "naver_news": news_result}
    finally:
        db.close()
