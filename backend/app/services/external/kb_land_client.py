"""PublicDataReader(pip install PublicDataReader)의 Kbland 래퍼로 KB부동산 데이터허브
주택가격동향조사(매매/전세/월세 가격지수)를 수집한다.

API 키가 필요 없는 공개 엔드포인트(data-api.kbland.kr)이며, PublicDataReader 내부 구현은
단순 GET 요청(verify=False) 후 pandas DataFrame으로 가공해 반환한다 - 실패 시 예외를 던지는
대신 내부에서 print(e)만 하고 None을 반환하므로, 이 래퍼에서 None을 감지해
KbLandApiError로 바꿔 던진다(다른 외부 클라이언트들과 동일한 호출 규약을 맞추기 위함).

월간주간구분코드는 항상 "01"(월간), 매물종별구분은 "98"(주택종합)로 고정한다 - 매매/전세는
이 조합으로 충분히 대표성이 있고, 월세는 KB가 아파트 전용 지수(get_monthly_apartment_wolse_index)만
제공해 매물종별구분 선택지가 없다.
"""

import logging

import pandas as pd
import PublicDataReader as pdr

logger = logging.getLogger(__name__)

_client = pdr.Kbland()

MONTHLY = "01"
HOUSING_TYPE_TOTAL = "98"  # 주택종합
TRADE_SALE = "01"
TRADE_JEONSE = "02"

TRADE_TYPE_LABELS = {TRADE_SALE: "매매", TRADE_JEONSE: "전세"}


class KbLandApiError(Exception):
    """KB부동산 데이터허브 API 호출 실패(네트워크 오류, 응답 형식 변경 등)를 의미한다."""


def _df_to_records(df: pd.DataFrame | None, context: str) -> list[dict]:
    if df is None:
        raise KbLandApiError(f"KB부동산 데이터허브 API 호출에 실패했습니다: {context}")
    df = df.copy()
    if "날짜" in df.columns:
        df["날짜"] = df["날짜"].dt.strftime("%Y-%m")
    return df.to_dict(orient="records")


def fetch_price_index(trade_type_code: str) -> list[dict]:
    """월간 주택종합 가격지수(매매=01/전세=02)를 시/도 단위 전 지역에 대해 가져온다."""
    df = _client.get_price_index(MONTHLY, HOUSING_TYPE_TOTAL, trade_type_code)
    return _df_to_records(df, f"가격지수(거래구분={TRADE_TYPE_LABELS.get(trade_type_code, trade_type_code)})")


def fetch_price_index_change_rate(trade_type_code: str) -> list[dict]:
    """월간 주택종합 가격지수의 전월 대비 증감률(%)을 시/도 단위 전 지역에 대해 가져온다."""
    df = _client.get_price_index_change_rate(MONTHLY, HOUSING_TYPE_TOTAL, trade_type_code)
    return _df_to_records(df, f"가격지수증감률(거래구분={TRADE_TYPE_LABELS.get(trade_type_code, trade_type_code)})")


def fetch_monthly_wolse_index() -> list[dict]:
    """월간 아파트 월세가격지수. 수도권(서울·경기·인천) 등 일부 지역만 제공된다 - 실측 확인됨."""
    df = _client.get_monthly_apartment_wolse_index()
    return _df_to_records(df, "월세가격지수")
