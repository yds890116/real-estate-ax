"""한국부동산원 R-ONE 부동산통계정보 Open API 클라이언트.

문서: https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do
- 엔드포인트: https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do (통계표 데이터 조회)
- 인증키(KEY)는 URL 인코딩 없이 그대로 사용 (온비드/국토부 공공데이터포털 서비스키와 달리 unquote 불필요)
- CORS/JSONP 미지원 - 서버(백엔드)에서만 호출 가능

실제 라이브 호출로 확인한 응답 필드(row 단위):
  STATBL_ID, DTACYCLE_CD, WRTTIME_IDTFR_ID(YYYYMM), CLS_ID(지역코드), CLS_NM(지역명),
  CLS_FULLNM(상위지역 포함 전체명, 예: "서울>강북지역>도심권>종로구"), ITM_ID, ITM_NM,
  DTA_VAL(지수값), UI_NM(단위), WRTTIME_DESC(예: "2026년 1월")
CLS_ID 없이 요청하면 전체 지역(시도/권역/시군구/구) 행이 한 번에 내려온다.
"""

import requests

from app.core.config import settings

BASE_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"


class RoneApiError(Exception):
    pass


MAX_PAGE_SIZE = 1000  # 라이브 호출로 확인됨: "데이터요청은 한번에 최대 1,000건을 넘을 수 없습니다" (ERROR-336)


def _fetch_page(statbl_id: str, dtacycle_cd: str, start_wrttime: str, end_wrttime: str, p_index: int) -> tuple[list[dict], int]:
    if not settings.RONE_API_KEY:
        raise RoneApiError("RONE_API_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    params = {
        "KEY": settings.RONE_API_KEY,
        "Type": "json",
        "pIndex": p_index,
        "pSize": MAX_PAGE_SIZE,
        "STATBL_ID": statbl_id,
        "DTACYCLE_CD": dtacycle_cd,
        "START_WRTTIME": start_wrttime,
        "END_WRTTIME": end_wrttime,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RoneApiError(f"R-ONE API 호출 실패: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise RoneApiError(f"R-ONE API 응답 파싱 실패: {e}") from e

    body = data.get("SttsApiTblData")
    if not body:
        raise RoneApiError(f"R-ONE API 응답 형식 오류: {data}")

    rows: list[dict] = []
    total_count = 0
    result_code = None
    result_msg = None
    for part in body:
        if "head" in part:
            for h in part["head"]:
                if "RESULT" in h:
                    result_code = h["RESULT"].get("CODE")
                    result_msg = h["RESULT"].get("MESSAGE")
                if "list_total_count" in h:
                    total_count = h["list_total_count"]
        if "row" in part:
            rows = part["row"]

    if result_code and not result_code.startswith("INFO-0"):
        raise RoneApiError(f"R-ONE API 오류 [{result_code}]: {result_msg}")

    return rows, total_count


def fetch_stats(statbl_id: str, dtacycle_cd: str, start_wrttime: str, end_wrttime: str) -> list[dict]:
    """통계표 하나를 조회해 원본 row 전체 목록(dict)을 반환한다 (1,000건 페이지 제한을 자동 페이지네이션).

    start_wrttime/end_wrttime: DTACYCLE_CD가 MM이면 YYYYMM 형식.
    """

    all_rows: list[dict] = []
    p_index = 1
    while True:
        rows, total_count = _fetch_page(statbl_id, dtacycle_cd, start_wrttime, end_wrttime, p_index)
        all_rows.extend(rows)
        if not rows or len(all_rows) >= total_count:
            break
        p_index += 1

    return all_rows
