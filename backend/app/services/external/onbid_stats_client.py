"""한국자산관리공사_차세대 온비드 지역별 입찰 통계 조회서비스 클라이언트.

문서: https://www.data.go.kr/data/15157756/openapi.do (data.go.kr 활용신청 상세기능정보)

확인된 사실 (data.go.kr 서비스 설명 페이지에서 확보):
- 필수 파라미터: statsTypeCd(재산유형 통계코드, 캠코 소관재산 조회 시 필수), inqPerd(조회기간: YYYY|YYYYMM|YYYY-Q)
- 응답은 지역별 감정가/최저입찰가/낙찰가/낙찰가율(감정가·최저입찰가 대비)/입찰참가자수/경쟁률 통계
  (동일 기관이 제공하는 파일데이터 "온비드 지역별 통계분석"과 동일 지표 구성으로 확인됨)
- 낙찰가율 200% 이상 또는 25% 미만인 물건은 통계 산정에서 제외됨

미확인 사항:
- 정확한 서비스/오퍼레이션(함수)명과 응답 XML/JSON 필드 영문 태그명. data.go.kr 상세기능정보 탭은
  로그인 세션이 필요한 JS 렌더링 화면이라 자동으로 확인할 수 없었다. app.core.config의
  ONBID_STATS_SERVICE/ONBID_STATS_FUNCTION은 KAMCO 명명 규칙에 기반한 잠정값이며,
  실제 값은 발급받은 'OpenAPI활용가이드' 문서에서 확인 후 backend/.env에서 교체하면 된다.
  (다른 온비드 API와 마찬가지로 openapi.onbid.co.kr 도메인이 현재 개발 네트워크에서 차단되어
  있어 최종 실호출 검증은 아직 하지 못했다.)
"""

import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests

from app.core.config import settings

BASE_URL = "http://openapi.onbid.co.kr/openapi/services"


class OnbidStatsApiError(Exception):
    pass


def fetch_regional_bid_stats(inq_perd: str, stats_type_cd: str | None = None, num_of_rows: int = 500, page_no: int = 1) -> list[dict[str, str]]:
    """지역별 입찰 통계를 조회해 원본 XML 필드를 dict로 반환.

    inq_perd: 조회기간 (YYYY | YYYYMM | YYYY-Q)
    stats_type_cd: 재산유형 통계코드 (캠코 소관재산 조회 시 필수, 이용기관재산은 생략 가능)
    """

    if not settings.ONBID_STATS_API_KEY:
        raise OnbidStatsApiError("ONBID_STATS_API_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    url = f"{BASE_URL}/{settings.ONBID_STATS_SERVICE}/{settings.ONBID_STATS_FUNCTION}"
    params = {
        "serviceKey": unquote(settings.ONBID_STATS_API_KEY),
        "inqPerd": inq_perd,
        "numOfRows": str(num_of_rows),
        "pageNo": str(page_no),
    }
    if stats_type_cd:
        params["statsTypeCd"] = stats_type_cd

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise OnbidStatsApiError(
            f"온비드 지역별 입찰 통계 API 호출 실패 (서비스/오퍼레이션명 미확정 상태 - "
            f"backend/.env의 ONBID_STATS_SERVICE/ONBID_STATS_FUNCTION 확인 필요): {e}"
        ) from e

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        raise OnbidStatsApiError(f"온비드 지역별 입찰 통계 API 응답 파싱 실패: {e}") from e

    result_code = root.findtext(".//resultCode")
    if result_code is not None and result_code not in ("00", "000"):
        result_msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        raise OnbidStatsApiError(f"온비드 지역별 입찰 통계 API 오류 [{result_code}]: {result_msg}")

    items = root.findall(".//item")
    return [{child.tag: (child.text or "").strip() for child in item} for item in items]
