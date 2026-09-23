"""카카오맵(로컬) API로 주소/단지명 검색어를 좌표·법정동코드로 변환한다.

- 정형 주소(예: "서울 강남구 대치동 943")는 주소검색 API가 b_code(법정동코드, 10자리)를
  직접 반환하므로 이를 그대로 사용한다. 별도의 정적 법정동코드 매핑 테이블을 만들지 않는 이유는
  카카오 API 자체가 전국 법정동코드를 공식 데이터로 이미 제공하기 때문이다(자체 테이블보다
  범위가 넓고 최신성도 보장된다).
- 아파트 단지명(예: "래미안대치팰리스")처럼 주소검색이 실패하는 입력은 키워드(장소) 검색으로
  좌표를 얻은 뒤, 좌표→행정구역 API(coord2regioncode)로 법정동코드를 역으로 조회한다.
"""

import dataclasses

import requests

from app.core.config import settings

BASE_URL = "https://dapi.kakao.com/v2/local"

# 주소검색(address.json)은 "서울", "경기" 같은 약칭을 반환하고, 좌표->행정구역 API는
# 정식 명칭("서울특별시", "경기도")을 반환해 서로 다르다. 앱 전체에서 sido는 정식 명칭으로
# 통일해 쓰므로(예: lawd_codes.py) 여기서 정규화한다.
SIDO_NORMALIZE = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "강원도": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _normalize_sido(name: str) -> str:
    return SIDO_NORMALIZE.get(name, name)


class KakaoApiError(Exception):
    pass


@dataclasses.dataclass
class LocationResult:
    query: str
    sido: str
    sigungu: str
    dong: str | None
    lawd_cd: str  # 법정동코드 앞 5자리 (시군구 코드)
    jibun: str | None  # 지번 (있는 경우)
    complex_name_hint: str | None  # 단지명 추정치 (건물명/장소명)
    x: str | None
    y: str | None
    source: str  # "address" | "keyword"


def _headers() -> dict[str, str]:
    if not settings.KAKAO_REST_API_KEY:
        raise KakaoApiError("KAKAO_REST_API_KEY가 설정되어 있지 않습니다. backend/.env를 확인해주세요.")
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


def _get(path: str, params: dict) -> dict:
    try:
        resp = requests.get(f"{BASE_URL}{path}", params=params, headers=_headers(), timeout=10)
    except requests.RequestException as e:
        raise KakaoApiError(f"카카오 API 호출 실패: {e}") from e

    if resp.status_code == 401:
        raise KakaoApiError("카카오 API 키가 유효하지 않습니다.")
    if not resp.ok:
        raise KakaoApiError(f"카카오 API 오류 [{resp.status_code}]: {resp.text[:200]}")

    return resp.json()


def _search_address(query: str) -> dict | None:
    data = _get("/search/address.json", {"query": query})
    documents = data.get("documents") or []
    return documents[0] if documents else None


@dataclasses.dataclass
class AutocompleteSuggestion:
    place_name: str  # 장소명(단지명 등) - 주소검색 결과면 지번주소를 그대로 씀
    address_name: str  # 지번주소
    road_address_name: str | None
    x: str
    y: str
    category_group_name: str | None


def search_autocomplete(query: str, size: int = 5) -> list[AutocompleteSuggestion]:
    """입력창 자동완성용 - 주소검색과 키워드(장소)검색 결과를 합쳐 상위 size개를 반환한다.

    카카오 로컬 API에는 전용 자동완성 엔드포인트가 없어(주소/키워드 검색만 제공), 두 검색을
    합쳐 자동완성처럼 보이게 구성한다. 주소검색 결과를 먼저 보여주고(정확도가 높음), 키워드
    검색 결과로 나머지 자리를 채운다(단지명 등 도로명/지번에 없는 입력 대응).
    """

    suggestions: list[AutocompleteSuggestion] = []
    seen: set[str] = set()

    try:
        addr_data = _get("/search/address.json", {"query": query, "size": min(size, 10)})
        for doc in addr_data.get("documents") or []:
            addr = doc["address"]
            road = doc.get("road_address") or {}
            key = addr.get("address_name", "")
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                AutocompleteSuggestion(
                    place_name=road.get("building_name") or addr.get("address_name", ""),
                    address_name=addr.get("address_name", ""),
                    road_address_name=road.get("address_name") or None,
                    x=addr.get("x", ""),
                    y=addr.get("y", ""),
                    category_group_name=None,
                )
            )
    except KakaoApiError:
        pass

    if len(suggestions) < size:
        try:
            kw_data = _get("/search/keyword.json", {"query": query, "size": min(size, 15)})
            for doc in kw_data.get("documents") or []:
                if len(suggestions) >= size:
                    break
                key = doc.get("address_name", "") or doc.get("place_name", "")
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append(
                    AutocompleteSuggestion(
                        place_name=doc.get("place_name", ""),
                        address_name=doc.get("address_name", ""),
                        road_address_name=doc.get("road_address_name") or None,
                        x=doc.get("x", ""),
                        y=doc.get("y", ""),
                        category_group_name=doc.get("category_group_name") or None,
                    )
                )
        except KakaoApiError:
            pass

    return suggestions[:size]


def _search_keyword(query: str) -> dict | None:
    data = _get("/search/keyword.json", {"query": query})
    documents = data.get("documents") or []
    return documents[0] if documents else None


def _coord_to_region_code(x: str, y: str) -> dict | None:
    data = _get("/geo/coord2regioncode.json", {"x": x, "y": y})
    documents = data.get("documents") or []
    for doc in documents:
        if doc.get("region_type") == "B":  # B=법정동, H=행정동
            return doc
    return documents[0] if documents else None


def resolve_location(query: str) -> LocationResult:
    address_doc = _search_address(query)
    if address_doc is not None:
        addr = address_doc["address"]
        road = address_doc.get("road_address") or {}
        jibun = addr.get("main_address_no") or None
        if jibun and addr.get("sub_address_no"):
            jibun = f"{jibun}-{addr['sub_address_no']}"

        return LocationResult(
            query=query,
            sido=_normalize_sido(addr["region_1depth_name"]),
            sigungu=addr["region_2depth_name"],
            dong=addr.get("region_3depth_name") or None,
            lawd_cd=addr["b_code"][:5],
            jibun=jibun,
            complex_name_hint=road.get("building_name") or None,
            x=addr.get("x"),
            y=addr.get("y"),
            source="address",
        )

    keyword_doc = _search_keyword(query)
    if keyword_doc is not None:
        x, y = keyword_doc.get("x"), keyword_doc.get("y")
        region_doc = _coord_to_region_code(x, y) if x and y else None
        if region_doc is None:
            raise KakaoApiError(f"'{query}'의 좌표는 찾았지만 법정동 정보를 확인하지 못했습니다.")

        return LocationResult(
            query=query,
            sido=_normalize_sido(region_doc["region_1depth_name"]),
            sigungu=region_doc["region_2depth_name"],
            dong=region_doc.get("region_3depth_name") or None,
            lawd_cd=region_doc["code"][:5],
            jibun=None,
            complex_name_hint=keyword_doc.get("place_name") or None,
            x=x,
            y=y,
            source="keyword",
        )

    raise KakaoApiError(f"'{query}'에 대한 주소/장소 검색 결과가 없습니다.")
