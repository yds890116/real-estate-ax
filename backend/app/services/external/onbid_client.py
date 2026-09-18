"""한국자산관리공사 온비드(OnBid) 공공데이터포털 API 클라이언트.

서비스: 이용기관공매물건 조회서비스(UtlinsttPblsalThingInquireSvc) - 물건목록(getPublicSaleObject)
문서: https://www.data.go.kr/data/15129871/openapi.do (온비드 물건정보 계열 서비스군)

공공데이터포털 서비스키는 계정 단위로 발급되며, 승인된 여러 API에 동일 키를 사용할 수 있다
(MOLIT_SERVICE_KEY와 동일 값이 개발요건서에 온비드용으로도 기재되어 있음).

주의: 온비드 API는 KAMCO 자체 도메인(openapi.onbid.co.kr)에서 서비스되며 apis.data.go.kr을
경유하지 않는다. 개발 환경(사내망/샌드박스)에 따라 해당 도메인으로의 아웃바운드 연결 자체가
막혀 있을 수 있으므로, 연결 실패는 OnbidApiError로 구분해 상위 계층이 "수집 실패"로 명확히
기록하도록 한다.
"""

import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests

from app.core.config import settings

BASE_URL = "http://openapi.onbid.co.kr/openapi/services/UtlinsttPblsalThingInquireSvc/getPublicSaleObject"


class OnbidApiError(Exception):
    pass


def fetch_public_sale_items(num_of_rows: int = 100, page_no: int = 1) -> list[dict[str, str]]:
    """공매 물건 목록(물건명, 소재지, 감정가, 최저입찰가 등)을 조회해 원본 XML 필드를 dict로 반환."""

    if not settings.ONBID_SERVICE_KEY:
        raise OnbidApiError("ONBID_SERVICE_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    params = {
        "serviceKey": unquote(settings.ONBID_SERVICE_KEY),
        "numOfRows": str(num_of_rows),
        "pageNo": str(page_no),
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise OnbidApiError(f"온비드 API 호출 실패: {e}") from e

    try:
        # molit_client와 동일하게 response.content를 그대로 파싱해 한글 인코딩 손상을 방지한다.
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        raise OnbidApiError(f"온비드 API 응답 파싱 실패: {e}") from e

    result_code = root.findtext(".//resultCode")
    if result_code is not None and result_code not in ("00", "000"):
        result_msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        raise OnbidApiError(f"온비드 API 오류 [{result_code}]: {result_msg}")

    items = root.findall(".//item")
    return [{child.tag: (child.text or "").strip() for child in item} for item in items]
