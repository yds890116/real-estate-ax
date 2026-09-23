"""호갱노노 단지 시세·매물 조회 오케스트레이션.

카카오 API로 좌표를 얻은 뒤(이미 이 프로젝트에서 검증된 kakao_client.resolve_location 재사용)
그 좌표로 호갱노노 지도를 이동시켜 단지별 실거래가/포털시세와 개별 매물 목록을 함께 가져온다.
이름이 정확히 일치하는 단지를 우선 찾고, 없으면 부분 일치로 폴백한다(매칭 로직 자체는
hogangnono_client._match_complex_items에 있다 - 매물 목록을 가져오려면 매칭된 단지의 id가
필요해 클라이언트 쪽에서 매칭까지 마치고 반환한다).
"""

from app.schemas.hogangnono import HogangnonoAreaPrice, HogangnonoComplexResult, HogangnonoListingItem
from app.services.external.hogangnono_client import HogangnonoBlockedError, fetch_complex_data
from app.services.external.kakao_client import KakaoApiError, resolve_location

TRADE_TYPE_LABELS = {0: "매매", 1: "전세", 2: "월세"}


def _parse_listing(raw: dict) -> HogangnonoListingItem | None:
    item_ids = raw.get("itemIds") or []
    item_id = item_ids[0].get("itemId") if item_ids else None
    if item_id is None or raw.get("privateArea") is None:
        return None

    trade_type_code = raw.get("tradeType")
    trade_type = TRADE_TYPE_LABELS.get(trade_type_code, "기타")
    rent = raw.get("rent") or 0

    return HogangnonoListingItem(
        item_id=item_id,
        trade_type=trade_type,
        price=raw.get("deposit") or 0,
        monthly_rent=rent if trade_type_code == 2 and rent > 0 else None,
        private_area=raw["privateArea"],
        public_area=raw.get("publicArea"),
        floor_tier=raw.get("floor"),
        dong_name=raw.get("aptDongName"),
        room_type=raw.get("danjiRoomType"),
        title=raw.get("itemTitle"),
    )


def get_complex_price(query: str, complex_name_hint: str | None = None) -> HogangnonoComplexResult:
    try:
        location = resolve_location(query)
    except KakaoApiError as e:
        return HogangnonoComplexResult(found=False, notice=f"위치를 확인하지 못했습니다: {e}")

    if not location.x or not location.y:
        return HogangnonoComplexResult(found=False, notice="좌표를 확인하지 못해 호갱노노 시세를 조회할 수 없습니다.")

    target_name = complex_name_hint or location.complex_name_hint or query

    try:
        result = fetch_complex_data(target_name, float(location.y), float(location.x))
    except HogangnonoBlockedError as e:
        return HogangnonoComplexResult(found=False, notice=f"호갱노노 조회에 실패했습니다: {e}")

    matched = result["matched_items"]
    if not matched:
        return HogangnonoComplexResult(found=False, notice=f"호갱노노에서 '{target_name}' 단지를 찾지 못했습니다.")

    first = matched[0]
    areas = []
    for it in matched:
        area = it.get("area") or {}
        if area.get("no") is None or area.get("private_area") is None:
            continue
        areas.append(
            HogangnonoAreaPrice(
                area_no=area["no"],
                private_area=area["private_area"],
                real_trade_price=area.get("real_trade_price") or None,
                portal_trade_price=area.get("portal_trade_price") or None,
                real_rent_price=area.get("real_rent_price") or None,
                portal_rent_price=area.get("portal_rent_price") or None,
            )
        )
    areas.sort(key=lambda a: a.private_area)

    listings = [parsed for raw in result["listings"] if (parsed := _parse_listing(raw)) is not None]
    listings.sort(key=lambda x: (x.private_area, x.trade_type))

    return HogangnonoComplexResult(
        found=True,
        complex_name=first.get("name"),
        address=first.get("address"),
        road_address=first.get("road_address"),
        total_household=first.get("total_household"),
        areas=areas,
        listings=listings,
        notice="호갱노노에서 실시간 수집한 실거래가·포털시세·매물 정보입니다.",
    )
