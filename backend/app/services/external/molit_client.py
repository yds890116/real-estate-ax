"""국토교통부 실거래가 상세 자료 Open API 클라이언트 (공공데이터포털).

- 아파트 매매: https://www.data.go.kr/data/15057511/openapi.do
- 아파트 전월세: https://www.data.go.kr/data/15058017/openapi.do
- 토지 매매: https://www.data.go.kr/data/15057267/openapi.do
같은 서비스키(MOLIT_SERVICE_KEY)로 세 자료 모두 조회 가능하다 (RTMSDataSvc 계열은 공공데이터포털에서
"부동산 거래가격 정보" 묶음으로 함께 활용신청되는 경우가 많다).
"""

import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests

from app.core.config import settings

TRADE_BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
RENT_BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
LAND_TRADE_BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade"


class MolitApiError(Exception):
    pass


def _fetch_rows(base_url: str, lawd_cd: str, deal_ymd: str) -> list[dict[str, str]]:
    """lawd_cd: 법정동코드 5자리, deal_ymd: 거래년월 YYYYMM. 원본 XML 필드를 dict로 반환."""

    if not settings.MOLIT_SERVICE_KEY:
        raise MolitApiError("MOLIT_SERVICE_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    params = {
        "serviceKey": unquote(settings.MOLIT_SERVICE_KEY),
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": "1000",
        "pageNo": "1",
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise MolitApiError(f"국토교통부 API 호출 실패: {e}") from e

    try:
        # XML의 encoding="utf-8" 선언을 따르도록 bytes(content)를 그대로 파싱한다.
        # response.text는 헤더 기반 인코딩 추정으로 한글이 깨질 수 있다.
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        raise MolitApiError(f"국토교통부 API 응답 파싱 실패: {e}") from e

    result_code = root.findtext(".//resultCode")
    if result_code not in ("00", "000"):
        result_msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        raise MolitApiError(f"국토교통부 API 오류 [{result_code}]: {result_msg}")

    items = root.findall(".//item")
    return [{child.tag: (child.text or "").strip() for child in item} for item in items]


def fetch_apt_trade_rows(lawd_cd: str, deal_ymd: str) -> list[dict[str, str]]:
    """아파트 매매 실거래가 상세자료."""
    return _fetch_rows(TRADE_BASE_URL, lawd_cd, deal_ymd)


def fetch_apt_rent_rows(lawd_cd: str, deal_ymd: str) -> list[dict[str, str]]:
    """아파트 전월세 실거래가 자료."""
    return _fetch_rows(RENT_BASE_URL, lawd_cd, deal_ymd)


def fetch_land_trade_rows(lawd_cd: str, deal_ymd: str) -> list[dict[str, str]]:
    """토지 매매 실거래가 자료."""
    return _fetch_rows(LAND_TRADE_BASE_URL, lawd_cd, deal_ymd)
