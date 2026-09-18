"""온비드 지역별 입찰 통계 샘플 데이터 생성기.

실제 수집은 app/services/external/onbid_stats_client.py가 담당하지만, 서비스/오퍼레이션명이
아직 미확정이고 개발 환경에서 openbid.co.kr 접속 자체가 막혀 있어(app/services/external/
onbid_client.py와 동일한 제약) 검증된 실호출이 불가능하다. CLAUDE.md의 "공식 API가 없는
데이터는 초기엔 샘플/더미 데이터로 화면과 로직부터 구현" 원칙에 따라, 지역별 트렌드 화면과
집계 로직을 먼저 검증할 수 있도록 현실적인 범위의 샘플 통계를 생성한다 (naver_listings.py와
동일한 시드 고정 방식).
"""

import hashlib
import random

SIDO_LIST = ["서울특별시", "경기도", "인천광역시", "부산광역시", "대구광역시", "대전광역시", "광주광역시"]

# 시도별 기준 낙찰가율(감정가 대비, %) - 수도권일수록 다소 높게, 최근 부동산 시황을 대략 반영한 참고값
BASE_BID_RATE = {
    "서울특별시": 92,
    "경기도": 87,
    "인천광역시": 82,
    "부산광역시": 78,
    "대구광역시": 74,
    "대전광역시": 79,
    "광주광역시": 76,
}

RECENT_MONTHS_COUNT = 6


def _recent_periods(count: int) -> list[str]:
    from datetime import date

    today = date.today()
    year, month = today.year, today.month
    periods = []
    for _ in range(count):
        periods.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(periods))


def get_sample_regional_stats(sido: str) -> list[dict]:
    """sido 하나에 대한 최근 RECENT_MONTHS_COUNT개월치 샘플 통계를 생성한다."""

    seed = int(hashlib.sha1(sido.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    base_rate = BASE_BID_RATE.get(sido, 80)
    periods = _recent_periods(RECENT_MONTHS_COUNT)

    rows = []
    for period in periods:
        bid_count = rng.randint(15, 120)
        win_count = round(bid_count * rng.uniform(0.35, 0.6))
        win_rate = round(win_count / bid_count * 100, 1) if bid_count else None

        avg_appraisal = rng.randint(300, 2500)  # 백만원
        rate_vs_appraisal = round(base_rate + rng.uniform(-6, 6), 1)
        rate_vs_appraisal = min(max(rate_vs_appraisal, 25), 200)  # API 설명상 통계 제외 구간과 동일하게 클램프
        avg_win_bid = round(avg_appraisal * rate_vs_appraisal / 100)
        avg_min_bid = round(avg_appraisal * rng.uniform(0.6, 0.75))
        rate_vs_min_bid = round(avg_win_bid / avg_min_bid * 100, 1) if avg_min_bid else None

        bidder_count = round(win_count * rng.uniform(1.5, 3.2))
        competition_rate = round(bidder_count / win_count, 2) if win_count else None

        rows.append(
            {
                "sido": sido,
                "sigungu": None,
                "period": period,
                "period_type": "month",
                "stats_type_cd": None,
                "bid_count": bid_count,
                "win_count": win_count,
                "win_rate": win_rate,
                "avg_appraisal_amt": avg_appraisal,
                "avg_min_bid_amt": round(avg_min_bid),
                "avg_win_bid_amt": avg_win_bid,
                "avg_bid_rate_vs_appraisal": rate_vs_appraisal,
                "avg_bid_rate_vs_min_bid": rate_vs_min_bid,
                "bidder_count": bidder_count,
                "competition_rate": competition_rate,
                "source": "sample",
            }
        )
    return rows


def get_all_sample_regional_stats() -> list[dict]:
    rows = []
    for sido in SIDO_LIST:
        rows.extend(get_sample_regional_stats(sido))
    return rows
