"""한국자산관리공사 온비드(OnBid) 공공데이터포털 API 클라이언트.

서비스: 이용기관공매물건 조회서비스(UtlinsttPblsalThingInquireSvc) - 물건목록(getPublicSaleObject)
       물건정보 조회서비스(ThingInfoInquireSvc) - 통합용도별물건감정평가서정보상세(getUnifyUsageCltrEstimationInfoDetail)
문서: https://www.data.go.kr/data/15129871/openapi.do (온비드 물건정보 계열 서비스군)

공공데이터포털 서비스키는 계정 단위로 발급되며, 승인된 여러 API에 동일 키를 사용할 수 있다
(MOLIT_SERVICE_KEY와 동일 값이 개발요건서에 온비드용으로도 기재되어 있음).

주의: 온비드 API는 KAMCO 자체 도메인(openapi.onbid.co.kr)에서 서비스되며 apis.data.go.kr을
경유하지 않는다. 개발 환경(사내망/샌드박스)에 따라 해당 도메인으로의 아웃바운드 연결 자체가
막혀 있을 수 있으므로, 연결 실패는 OnbidApiError로 구분해 상위 계층이 "수집 실패"로 명확히
기록하도록 한다.

감정평가서 "원문 PDF 다운로드"는 이 API 계열에서 안정적인 다운로드 URL 필드를 확인하지 못해
(문서 접근이 막혀 최종 검증 불가) 이번 구현에서는 제외했다. 대신 통합용도별물건감정평가서정보상세
기능으로 감정가·감정평가일자·감정평가업체 같은 구조화된 감정평가 기준정보를 수집한다 - 이 값들이
스코어링 모델의 핵심 피처(실제 온비드가 공식 인정한 감정가·평가시점)로는 PDF 원문보다 오히려
더 바로 쓸 수 있는 형태다.
"""

import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests

from app.core.config import settings

SERVICES_BASE = "http://openapi.onbid.co.kr/openapi/services"
PUBLIC_SALE_URL = f"{SERVICES_BASE}/UtlinsttPblsalThingInquireSvc/getPublicSaleObject"
APPRAISAL_DETAIL_URL = f"{SERVICES_BASE}/ThingInfoInquireSvc/getUnifyUsageCltrEstimationInfoDetail"


class OnbidApiError(Exception):
    pass


def _fetch_items(url: str, params: dict[str, str]) -> list[dict[str, str]]:
    if not settings.ONBID_SERVICE_KEY:
        raise OnbidApiError("ONBID_SERVICE_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    request_params = {"serviceKey": unquote(settings.ONBID_SERVICE_KEY), **params}

    try:
        response = requests.get(url, params=request_params, timeout=15)
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


def fetch_public_sale_items(num_of_rows: int = 100, page_no: int = 1) -> list[dict[str, str]]:
    """공매 물건 목록(물건명, 소재지, 감정가, 최저입찰가 등)을 조회해 원본 XML 필드를 dict로 반환."""

    return _fetch_items(PUBLIC_SALE_URL, {"numOfRows": str(num_of_rows), "pageNo": str(page_no)})


def fetch_appraisal_detail(cltr_mnmt_no: str) -> dict[str, str] | None:
    """물건 1건의 감정평가 기준정보(감정가/감정평가일자/감정평가업체)를 조회한다.

    요청 파라미터명(CLTR_MNMT_NO로 단건 조회 가능하다는 가정)과 응답 필드명(APSL_ASES_AMT,
    APSL_ASES_DT, APSL_ASES_ORG_NM)은 공공데이터포털 문서 페이지 접근이 막혀 최종 라이브
    검증을 하지 못했다 - PublicDataReader 라이브러리의 kamco.py 참고 자료 기준 잠정값이다.
    실제 값과 다르면 조용히 빈 dict로 끝나는 대신 OnbidApiError가 나므로 상위 호출부의
    try/except에서 그대로 실패로 기록된다.
    """

    items = _fetch_items(APPRAISAL_DETAIL_URL, {"CLTR_MNMT_NO": cltr_mnmt_no, "numOfRows": "10", "pageNo": "1"})
    return items[0] if items else None
