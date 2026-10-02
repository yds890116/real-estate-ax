"""일일/주간 데이터 수집 배치를 새벽 시간대에 자동 실행하는 스케줄러.

BackgroundScheduler를 사용한다: FastAPI가 동기 워커(uvicorn 기본)로 실행되고, 배치 작업 자체도
동기 SQLAlchemy 세션을 쓰므로 별도 이벤트루프 없이 백그라운드 스레드에서 도는 편이 단순하다.

- daily_data_collection: 온비드 공매물건·네이버 뉴스 (매일)
- weekly_onbid_regional_stats: 온비드 지역별 입찰 통계 (월 단위 집계라 갱신이 느려 주 1회면 충분)
- monthly_rone_price_index: 한국부동산원 R-ONE 지역별 주택가격지수 (월 단위 집계라 월 1회면 충분)
"""

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.services.batch_collection_service import run_daily_collection_job

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _run_daily_job_with_logging() -> None:
    logger.info("일일 데이터 수집 배치 시작")
    try:
        result = run_daily_collection_job()
        logger.info("일일 데이터 수집 배치 완료: %s", result)
    except Exception:
        logger.exception("일일 데이터 수집 배치 실행 중 예외 발생")


def _run_weekly_regional_stats_job() -> None:
    from app.db.session import SessionLocal
    from app.services.regional_stats_service import collect_onbid_regional_stats

    logger.info("온비드 지역별 입찰 통계 주간 배치 시작")
    db = SessionLocal()
    try:
        inq_perd = date.today().strftime("%Y%m")
        result = collect_onbid_regional_stats(db, inq_perd)
        logger.info("온비드 지역별 입찰 통계 주간 배치 완료: %s", result)
    except Exception:
        logger.exception("온비드 지역별 입찰 통계 주간 배치 실행 중 예외 발생")
    finally:
        db.close()


def _run_monthly_rone_price_index_job() -> None:
    from app.db.session import SessionLocal
    from app.services.rone_index_service import collect_regional_indicators, collect_regional_price_indices

    logger.info("R-ONE 지역별 주택가격지수 월간 배치 시작")
    db = SessionLocal()
    try:
        result = collect_regional_price_indices(db)
        indicator_result = collect_regional_indicators(db)
        logger.info("R-ONE 지역별 주택가격지수 월간 배치 완료: %s / 지가변동률·임대동향지수: %s", result, indicator_result)
    except Exception:
        logger.exception("R-ONE 지역별 주택가격지수 월간 배치 실행 중 예외 발생")
    finally:
        db.close()


def _run_monthly_kb_price_index_job() -> None:
    from app.db.session import SessionLocal
    from app.services.kb_stats_service import collect_kb_price_indices

    logger.info("KB부동산 매매/전세/월세 가격지수 월간 배치 시작")
    db = SessionLocal()
    try:
        result = collect_kb_price_indices(db)
        logger.info("KB부동산 매매/전세/월세 가격지수 월간 배치 완료: %s", result)
    except Exception:
        logger.exception("KB부동산 매매/전세/월세 가격지수 월간 배치 실행 중 예외 발생")
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        _run_daily_job_with_logging,
        trigger="cron",
        hour=settings.BATCH_SCHEDULE_HOUR,
        minute=settings.BATCH_SCHEDULE_MINUTE,
        id="daily_data_collection",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_weekly_regional_stats_job,
        trigger="cron",
        day_of_week=settings.ONBID_STATS_SCHEDULE_DAY_OF_WEEK,
        hour=settings.ONBID_STATS_SCHEDULE_HOUR,
        minute=settings.ONBID_STATS_SCHEDULE_MINUTE,
        id="weekly_onbid_regional_stats",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_monthly_rone_price_index_job,
        trigger="cron",
        day=settings.RONE_SCHEDULE_DAY,
        hour=settings.RONE_SCHEDULE_HOUR,
        minute=settings.RONE_SCHEDULE_MINUTE,
        id="monthly_rone_price_index",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_monthly_kb_price_index_job,
        trigger="cron",
        day=settings.KB_STATS_SCHEDULE_DAY,
        hour=settings.KB_STATS_SCHEDULE_HOUR,
        minute=settings.KB_STATS_SCHEDULE_MINUTE,
        id="monthly_kb_price_index",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "데이터 수집 배치 스케줄 등록 완료: 일일 %02d:%02d / 지역별 입찰통계 매주 %d요일 %02d:%02d / "
        "R-ONE 지역별 주택가격지수 매월 %d일 %02d:%02d / KB부동산 가격지수 매월 %d일 %02d:%02d (Asia/Seoul)",
        settings.BATCH_SCHEDULE_HOUR,
        settings.BATCH_SCHEDULE_MINUTE,
        settings.ONBID_STATS_SCHEDULE_DAY_OF_WEEK,
        settings.ONBID_STATS_SCHEDULE_HOUR,
        settings.ONBID_STATS_SCHEDULE_MINUTE,
        settings.RONE_SCHEDULE_DAY,
        settings.RONE_SCHEDULE_HOUR,
        settings.RONE_SCHEDULE_MINUTE,
        settings.KB_STATS_SCHEDULE_DAY,
        settings.KB_STATS_SCHEDULE_HOUR,
        settings.KB_STATS_SCHEDULE_MINUTE,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
