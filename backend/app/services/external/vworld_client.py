"""국토교통부 공간정보 오픈플랫폼 브이월드(V-World) 2D 데이터 API로 토지특성정보를 조회한다.

실제 키로 라이브 검증 완료(중요, 반드시 읽고 사용할 것):
- 인증 시 `domain` 파라미터가 필수다 - 키 발급 시 등록한 서비스 도메인과 일치해야 하며,
  빠뜨리면 "인증키 정보가 올바르지 않습니다"라는 오해하기 쉬운 오류가 난다(실제로는 키 자체가
  아니라 domain 누락이 원인이었다). settings.VWORLD_DOMAIN(기본값 "localhost")을 쓴다.
- 연속지적도(LP_PA_CBND_BUBUN)는 지목을 별도 필드로 주지 않는다 - jibun 필드에 "1027 대"처럼
  지번 뒤에 지목 한 글자(대/전/답/임 등)가 공백으로 붙어서 온다. 이 클라이언트가 분리해 반환한다.
  공시지가는 jiga 필드(원/㎡), 공시기준일은 gosi_year+gosi_month.
- 토지이용계획도(LT_C_LHBLPN)로 용도지역을 조회하려던 최초 설계는 실제로는 해당 서비스ID가
  NOT_FOUND만 반환해 폐기했다. 대신 용도지역 4대 분류 레이어(도시/관리/농림/자연환경보전,
  LT_C_UQ111~114)를 순서대로 좌표 조회하면 맨 처음 매치되는 레이어의 `uname` 속성이
  "제3종일반주거지역"처럼 세분류 명칭까지 정확히 담겨 있음을 실측으로 확인했다(용도지역
  상한표 app/core/land_use_reference.py의 키와 그대로 일치한다).

좌표 기반(geomFilter=POINT) 조회를 쓴다 - PNU 텍스트 조합(법정동코드+산여부+본번+부번) 없이도
카카오에서 받은 x,y 좌표만으로 바로 질의할 수 있어, 아파트 단지명처럼 지번을 모르는 입력에도
동작한다(hogangnono_client.py가 좌표 기반으로 지도를 이동시키는 것과 같은 이유의 선택).
"""

import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "http://api.vworld.kr/req/data"

SVC_CADASTRAL = "LP_PA_CBND_BUBUN"  # 연속지적도 (지목/지번/공시지가)

# 용도지역 4대 분류 - 순서대로 조회해 처음 매치되는 레이어를 쓴다(한 지점은 하나에만 속한다).
SVC_LAND_USE_ZONES = ["LT_C_UQ111", "LT_C_UQ112", "LT_C_UQ113", "LT_C_UQ114"]


class VWorldApiError(Exception):
    """V-World API 호출 실패(네트워크 오류, 키 미설정, 응답 형식 변경 등)를 의미한다."""


def _get_features(data_id: str, x: str, y: str) -> list[dict]:
    if not settings.VWORLD_API_KEY:
        raise VWorldApiError("VWORLD_API_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": data_id,
        "key": settings.VWORLD_API_KEY,
        "domain": settings.VWORLD_DOMAIN,
        "geomFilter": f"POINT({x} {y})",
        "crs": "EPSG:4326",
        "format": "json",
        "size": "1",
    }
    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        raise VWorldApiError(f"V-World API 호출 실패: {e}") from e

    try:
        body = res.json()
    except ValueError as e:
        raise VWorldApiError(f"V-World API 응답 파싱 실패: {e}") from e

    status = (body.get("response") or {}).get("status")
    if status == "NOT_FOUND":
        return []
    if status != "OK":
        error_msg = (body.get("response") or {}).get("error", {}).get("text", "알 수 없는 오류")
        raise VWorldApiError(f"V-World API 오류 [{status}]: {error_msg}")

    result = (body.get("response") or {}).get("result") or {}
    features = (result.get("featureCollection") or {}).get("features") or []
    return features


def fetch_cadastral_info(x: str, y: str) -> dict | None:
    """좌표가 속한 필지의 지목/지번/개별공시지가를 연속지적도에서 조회한다. 결과 없으면 None."""

    features = _get_features(SVC_CADASTRAL, x, y)
    if not features:
        return None

    props = features[0].get("properties") or {}
    jibun_raw = (props.get("jibun") or "").strip()
    jibun, _, jimok = jibun_raw.rpartition(" ")  # "1027 대" -> ("1027", " ", "대")
    if not jibun:  # 구분자가 없으면(공백 없음) 전체를 지번으로 보고 지목은 비워둔다
        jibun, jimok = jibun_raw, None

    jiga = props.get("jiga")
    return {
        "pnu": props.get("pnu"),
        "jibun": jibun or None,
        "jimok": jimok or None,
        "addr": props.get("addr"),
        "gosi_year": props.get("gosi_year"),
        "gosi_month": props.get("gosi_month"),
        "jiga": int(jiga) if jiga else None,
    }


def fetch_land_use_zone(x: str, y: str) -> dict | None:
    """좌표가 속한 용도지역(세분류)을 도시/관리/농림/자연환경보전지역 레이어에서 순서대로 조회한다.

    결과 없으면 None. 용도지구(land_use_district)는 별도 레이어(경관지구 등 10여 종)로 나뉘어 있어
    이번 범위에서는 조회하지 않는다 - 값은 항상 None으로 반환되며, 필요해지면 보완한다.
    """

    for data_id in SVC_LAND_USE_ZONES:
        features = _get_features(data_id, x, y)
        if not features:
            continue
        props = features[0].get("properties") or {}
        zone_name = props.get("uname")
        if zone_name:
            return {"land_use_zone": zone_name, "land_use_district": None}

    return None
