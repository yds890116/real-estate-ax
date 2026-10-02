"""토지가치평가 통합 서비스.

브이월드(지목/용도지역/개별공시지가) + 카카오맵(최근접 지하철역 거리/도로유형) + R-ONE(지가변동률,
이미 수집된 지역 지표 재사용) + 국토교통부(토지 실거래가)를 묶어 "토지 가치평가 점수"를 산출하고,
risk_indicators.land_value()가 리스크 스코어링에 반영할 수 있는 0~100 점수로 환산해 돌려준다.

외부 API 중 하나라도 실패해도(키 미설정, 네트워크 오류, 해당 좌표에 데이터 없음 등) 전체
분석 요청이 막히지 않도록 단계별로 예외를 흡수하고, 값을 구하지 못한 항목은 None으로 비워둔다
(가짜 값을 채우지 않는다) - 이 프로젝트의 다른 외부 연동과 동일한 원칙.
"""

import logging
import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.land_use_reference import DEFAULT_FAR_BCR_CAP, LEGAL_FAR_BCR_CAPS
from app.schemas.land_valuation import DevelopmentPotential, LandCharacteristics, LandValuationResult, LocationValue
from app.schemas.property import PropertyBase
from app.services.external.kakao_client import KakaoApiError, find_nearest_subway_station, resolve_location
from app.services.external.molit_client import MolitApiError, fetch_land_trade_rows
from app.services.external.vworld_client import VWorldApiError, fetch_cadastral_info, fetch_land_use_zone
from app.services.rone_index_service import get_region_trend_features

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "⚠ 지목·용도지역·개별공시지가는 브이월드(V-World) 공개 데이터 기준이며, 법정 용적률·건폐율 상한은 "
    "국토의 계획 및 이용에 관한 법률 시행령 기준 참고치입니다(지자체 조례로 더 낮게 세분화될 수 있음). "
    "개발잠재력·입지가치·종합 토지가치평가점수는 참고용 AI 추정치이며 실제 개발행위허가 가능 여부와 "
    "다를 수 있습니다."
)


def _road_type(road_address_name: str | None) -> str | None:
    """도로명주소에서 도로 유형(대로/로/길)을 추정한다 - 카카오 로컬 API에는 도로 자체에 대한
    POI/거리 조회가 없어, 건물이 접한 도로명의 어미(대로/로/길)로 간선도로 인접 여부를 근사한다."""

    if not road_address_name:
        return None
    # "OO대로 123" / "OO로 45길 6" / "OO길 12" 패턴에서 번지 앞 도로명 토큰을 찾는다.
    match = re.search(r"([가-힣0-9]+(?:대로|로|길))\s*\d", road_address_name)
    if not match:
        return None
    road_name = match.group(1)
    if road_name.endswith("대로"):
        return "대로"
    if road_name.endswith("길"):
        return "길"
    return "로"


def _location_value_score(subway: tuple[str, float] | None, road_type: str | None) -> float | None:
    if subway is None and road_type is None:
        return None

    subway_score = 50.0  # 지하철역 정보 없으면 중립
    if subway is not None:
        _, distance_m = subway
        if distance_m <= 500:
            subway_score = 100.0
        elif distance_m <= 1000:
            subway_score = 70.0
        elif distance_m <= 2000:
            subway_score = 40.0
        else:
            subway_score = 15.0

    road_score = {"대로": 100.0, "로": 60.0, "길": 30.0}.get(road_type, 50.0)

    return round(subway_score * 0.6 + road_score * 0.4, 1)


def _development_potential(land_use_zone: str | None, current_floors: int | None) -> DevelopmentPotential:
    if land_use_zone is None:
        return DevelopmentPotential(notice="용도지역을 확인하지 못해 개발잠재력 지수를 산출할 수 없습니다.")

    bcr_cap, far_cap = LEGAL_FAR_BCR_CAPS.get(land_use_zone, DEFAULT_FAR_BCR_CAP)
    implied_max_floors = round(far_cap / bcr_cap, 1) if bcr_cap else None

    if current_floors is None or implied_max_floors is None:
        return DevelopmentPotential(
            legal_bcr_cap_pct=bcr_cap,
            legal_far_cap_pct=far_cap,
            implied_max_floors=implied_max_floors,
            notice="현재 건축물 층수 정보가 없어 활용률·개발잠재력 지수를 산출할 수 없습니다 (법정 상한만 참고로 제공).",
        )

    utilization_ratio = round(min(150.0, current_floors / implied_max_floors * 100), 1)
    development_potential_index = round(max(0.0, min(100.0, 100 - utilization_ratio)), 1)

    return DevelopmentPotential(
        legal_bcr_cap_pct=bcr_cap,
        legal_far_cap_pct=far_cap,
        current_floors=current_floors,
        implied_max_floors=implied_max_floors,
        utilization_ratio_pct=utilization_ratio,
        development_potential_index=development_potential_index,
        notice=(
            f"법정 용적률 상한({far_cap}%) ÷ 건폐율 상한({bcr_cap}%)으로 추정한 평균 최대 층수"
            f"({implied_max_floors}층) 대비 현재 층수({current_floors}층)의 비율로 산출한 참고 지표입니다. "
            "이 방식은 건물이 대지 전체를 법정 건폐율 상한까지 덮는다고 가정하므로, 건폐율을 낮게 쓰고 "
            "타워형으로 높이 올린 고층 아파트 단지는 실제보다 '개발여지가 거의 없다'고 낮게 나올 수 있습니다 "
            "(이미 지어진 고층 단지는 어차피 추가 개발 여지가 작다는 의미로는 방향성이 맞지만, 수치 자체를 "
            "그대로 신뢰하지 말고 참고용으로만 보세요)."
        ),
    )


def _recent_land_trade_avg_price(db: Session, lawd_cd: str) -> float | None:
    today = date.today()
    for months_back in range(0, 6):  # 최근 6개월 내에서 거래가 있는 가장 최근 월을 찾는다
        target = today.replace(day=1) - timedelta(days=months_back * 30)
        deal_ymd = target.strftime("%Y%m")
        try:
            rows = fetch_land_trade_rows(lawd_cd, deal_ymd)
        except MolitApiError as e:
            logger.info("토지 실거래가 조회 실패(%s, %s): %s", lawd_cd, deal_ymd, e)
            return None

        # 국토부 실거래가 상세자료 API는 영문 필드명을 쓴다(dealAmount, excluUseAr 등 - market_data_service.py와
        # 동일 계열 API). 토지 매매는 면적 필드명이 "dealArea" 계열일 가능성이 높아 여러 후보를 시도한다.
        prices_per_sqm = []
        for row in rows:
            try:
                amount = int((row.get("dealAmount") or "0").replace(",", "").strip())
                area_raw = row.get("dealArea") or row.get("area") or row.get("totalFloorAr")
                area = float(area_raw) if area_raw else 0.0
                if amount > 0 and area > 0:
                    prices_per_sqm.append(amount * 10000 / area)  # 거래금액 단위는 만원
            except (TypeError, ValueError):
                continue

        if prices_per_sqm:
            return round(sum(prices_per_sqm) / len(prices_per_sqm), 0)

    return None


def get_land_valuation(db: Session, prop: PropertyBase) -> LandValuationResult:
    try:
        location = resolve_location(prop.address)
    except KakaoApiError as e:
        characteristics = LandCharacteristics(available=False, notice=f"위치 확인 실패: {e}")
        development_potential = DevelopmentPotential(notice="위치 확인에 실패해 개발잠재력 지수를 산출할 수 없습니다.")
        location_value = LocationValue(notice="위치 확인에 실패해 입지가치 점수를 산출할 수 없습니다.")
        return LandValuationResult(
            characteristics=characteristics,
            development_potential=development_potential,
            location_value=location_value,
            disclaimer=DISCLAIMER,
        )

    # ── 지목·용도지역·개별공시지가 (V-World) ──────────────────────────────
    cadastral = None
    land_use = None
    vworld_error: str | None = None
    if location.x and location.y:
        try:
            cadastral = fetch_cadastral_info(location.x, location.y)
            land_use = fetch_land_use_zone(location.x, location.y)
        except VWorldApiError as e:
            vworld_error = str(e)
            logger.info("V-World 조회 실패: %s", e)

    if cadastral or land_use:
        characteristics = LandCharacteristics(
            pnu=(cadastral or {}).get("pnu"),
            jimok=(cadastral or {}).get("jimok"),
            land_use_zone=(land_use or {}).get("land_use_zone"),
            land_use_district=(land_use or {}).get("land_use_district"),
            official_land_price=int((cadastral or {}).get("jiga")) if (cadastral or {}).get("jiga") else None,
            official_land_price_base_date=(
                f"{(cadastral or {}).get('gosi_year')}-{(cadastral or {}).get('gosi_month')}"
                if (cadastral or {}).get("gosi_year")
                else None
            ),
            address=(cadastral or {}).get("addr"),
            available=True,
            notice="브이월드(V-World) 연속지적도·토지이용계획도 조회 결과입니다.",
        )
    else:
        notice = f"브이월드 조회 실패: {vworld_error}" if vworld_error else "해당 좌표의 토지특성 정보를 찾지 못했습니다."
        characteristics = LandCharacteristics(available=False, notice=notice)

    # ── 개발잠재력 지수 ────────────────────────────────────────────────────
    land_use_zone = characteristics.land_use_zone
    development_potential = _development_potential(land_use_zone, prop.total_floors)

    # ── 입지가치 (카카오: 최근접 지하철역 + 도로유형) ─────────────────────
    subway = None
    if location.x and location.y:
        try:
            subway = find_nearest_subway_station(location.x, location.y)
        except KakaoApiError as e:
            logger.info("최근접 지하철역 조회 실패: %s", e)

    road_type = _road_type(location.road_address_name)
    location_value_score = _location_value_score(subway, road_type)
    location_value = LocationValue(
        nearest_subway_name=subway[0] if subway else None,
        nearest_subway_distance_m=subway[1] if subway else None,
        road_type=road_type,
        location_value_score=location_value_score,
        notice="간선도로 접근성은 카카오맵에 도로 자체의 POI 거리 조회 기능이 없어, 건물이 접한 도로명 유형(대로/로/길)으로 근사했습니다.",
    )

    # ── 지가변동률 (R-ONE, 이미 수집된 지역 지표 재사용) ──────────────────
    regional_trend = get_region_trend_features(db, prop.sido, prop.sigungu)
    land_price_change_pct = regional_trend.get("land_price_change_latest")

    # ── 토지 실거래가 (국토교통부) ─────────────────────────────────────────
    land_trade_price_per_sqm = _recent_land_trade_avg_price(db, location.lawd_cd)

    # ── 종합 토지가치평가점수 (0~100, 높을수록 양호) ──────────────────────
    sub_scores = [s for s in [development_potential.development_potential_index, location_value_score] if s is not None]
    land_valuation_score = round(sum(sub_scores) / len(sub_scores), 1) if sub_scores else None

    return LandValuationResult(
        characteristics=characteristics,
        development_potential=development_potential,
        location_value=location_value,
        land_price_change_pct=land_price_change_pct,
        land_trade_price_per_sqm=land_trade_price_per_sqm,
        land_valuation_score=land_valuation_score,
        disclaimer=DISCLAIMER,
    )
