"""매일 새벽 자동 실행되는 데이터 수집 배치의 핵심 로직.

- 온비드 공매 물건·감정가 데이터 수집 (cltr_mnmt_no 물건관리번호 기준 중복 체크)
- 네이버 뉴스 검색 API로 부동산 정책 뉴스 수집 (link 기사 링크 기준 중복 체크)

각 수집 함수는 실행 1회당 batch_run_logs에 수집 건수/중복 건수/실패 건수를 기록한다.
개별 항목 처리 중 오류가 나도 전체 배치가 중단되지 않도록 항목 단위로 예외를 흡수한다.
"""

import html
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.batch_run_log import BatchRunLog
from app.models.news_article import NewsArticle
from app.models.onbid_auction_item import OnbidAuctionItem
from app.services.external.naver_news_client import NaverNewsApiError, fetch_news_items
from app.services.external.onbid_client import OnbidApiError, fetch_public_sale_items

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


def upsert_onbid_item(db: Session, raw: dict[str, str]) -> tuple[OnbidAuctionItem | None, bool]:
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
    )
    db.add(obj)
    db.flush()
    return obj, True


def collect_onbid_auction_items(db: Session, num_of_rows: int = 100) -> dict[str, int]:
    """온비드 공매 물건·감정가 데이터를 수집해 onbid_auction_items에 적재하고 실행 로그를 남긴다."""

    log = _start_log(db, "onbid_auction")
    collected = skipped = failed = 0
    error_messages: list[str] = []

    try:
        raw_rows = fetch_public_sale_items(num_of_rows=num_of_rows)
    except OnbidApiError as e:
        _finish_log(db, log, collected=0, skipped=0, failed=1, error_message=str(e))
        return {"collected": 0, "skipped": 0, "failed": 1, "status": log.status, "error": str(e)}

    for raw in raw_rows:
        try:
            _, was_new = upsert_onbid_item(db, raw)
            collected += 1 if was_new else 0
            skipped += 0 if was_new else 1
        except Exception as e:  # 항목 단위 오류는 배치 전체를 중단시키지 않는다
            failed += 1
            error_messages.append(str(e))

    db.commit()
    error_message = "; ".join(error_messages) or None
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
        news_result = collect_naver_news(db)
        return {"onbid_auction": onbid_result, "naver_news": news_result}
    finally:
        db.close()
