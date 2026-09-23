"""온비드 공매 물건 샘플 데이터 생성기.

이 개발 환경에서는 openapi.onbid.co.kr 아웃바운드 연결 자체가 막혀 있어(app/services/external/
onbid_client.py 상단 docstring 참고) 실제 수집이 전혀 되지 않는다. CLAUDE.md의 "공식 API가
없는 데이터는 초기엔 샘플/더미 데이터로 화면과 로직부터 구현" 원칙에 따라, 스코어링 모델
학습·화면 검증을 실제 네트워크 없이도 할 수 있도록 현실적인 상관관계를 가진 샘플 물건을
생성한다 (naver_listings.py/regional_stats_sample.py와 동일한 시드 고정 방식).

핵심 상관관계 설계 (학습이 의미를 갖도록):
- 유찰횟수(uscbd_cnt)가 많을수록 최저입찰가율(fee_rate)이 낮다 (회차마다 통상 20~30%씩 저감)
- 용도·처분방식에 따라 유찰 성향이 다르게 설계한다 (예: 토지/임야는 아파트보다 유찰이 잦음)
"""

import hashlib
import random
from datetime import datetime, timedelta, timezone

CATEGORIES = ["아파트", "오피스텔", "상가", "토지", "임야", "공장", "창고"]
SIDO_LIST = ["서울특별시", "경기도", "인천광역시", "부산광역시", "대구광역시", "충청남도", "전라남도"]
DPSL_METHODS = ["매각", "임대"]
BID_METHODS = ["일반경쟁(최고가방식)", "일반경쟁(제한적 최고가방식)"]

# 용도별 유찰 성향 (기대 유찰횟수의 상대적 배율) - 토지/임야류가 아파트보다 유찰이 잦다는 통념 반영
CATEGORY_USCBD_BIAS = {
    "아파트": 0.5,
    "오피스텔": 0.8,
    "상가": 1.3,
    "토지": 1.6,
    "임야": 2.0,
    "공장": 1.4,
    "창고": 1.2,
}

ITEM_COUNT = 320


def get_sample_onbid_items() -> list[dict]:
    rng = random.Random(int(hashlib.sha1(b"onbid_auction_sample_v1").hexdigest(), 16) % (2**32))

    rows = []
    for i in range(ITEM_COUNT):
        category = rng.choice(CATEGORIES)
        sido = rng.choice(SIDO_LIST)
        bias = CATEGORY_USCBD_BIAS[category]

        # 유찰횟수: 용도별 성향을 평균으로 하는 포아송 근사(간단히 정수 라운딩한 지수분포로 대체)
        uscbd_cnt = min(6, int(rng.expovariate(1 / max(bias, 0.1))))

        appraisal_amt = rng.randint(50_000_000, 3_000_000_000)  # 원
        # 회차마다 통상 20~30% 저감 - 유찰횟수에 비례해 최저입찰가율이 낮아진다
        fee_rate_pct = max(20.0, round(100 * (0.8 ** uscbd_cnt) * rng.uniform(0.95, 1.05), 1))
        min_bid_prc = round(appraisal_amt * fee_rate_pct / 100)

        item_no = f"SMP{i + 1:05d}"
        # "일자별 신규 매물" 화면이 의미 있게 보이도록 최근 14일에 걸쳐 등록일을 흩뿌린다
        # (최근 날짜일수록 더 많이 등록된 것처럼 - 실제 매일 배치가 쌓이는 모습과 비슷하게).
        days_ago = rng.choices(range(14), weights=[14 - d for d in range(14)])[0]
        collected_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=rng.uniform(0, 20))

        rows.append(
            {
                "CLTR_MNMT_NO": item_no,
                "_COLLECTED_AT": collected_at,
                "PLNM_NO": f"P{2026}{i % 50:04d}",
                "PBCT_NO": f"B{i:06d}",
                "CLTR_NM": f"{sido} {category} 물건 {i + 1}",
                "CTGR_FULL_NM": category,
                "LDNM_ADRS": f"{sido} 샘플구 샘플동 {i + 1}",
                "NMRD_ADRS": f"{sido} 샘플대로 {i + 1}길",
                "DPSL_MTD_NM": rng.choice(DPSL_METHODS),
                "BID_MTD_NM": rng.choice(BID_METHODS),
                "MIN_BID_PRC": str(min_bid_prc),
                "APSL_ASES_AVG_AMT": str(appraisal_amt),
                "FEE_RATE": f"{fee_rate_pct}",
                "PBCT_BEGN_DTM": "20260101090000",
                "PBCT_CLS_DTM": "20260103170000",
                "PBCT_CLTR_STAT_NM": "유찰" if uscbd_cnt > 0 and rng.random() < 0.3 else "입찰진행",
                "USCBD_CNT": str(uscbd_cnt),
            }
        )
    return rows
