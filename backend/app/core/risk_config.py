"""담보 리스크 스코어링 v2 설정 — 카테고리/지표 가중치와 기준값을 로직(risk_engine.py,
risk_indicators.py)에서 분리해 이후 가중치만 조정하고 싶을 때 이 파일만 고치면 되게 한다.

카테고리 가중치 합계와 각 카테고리 내부 지표 가중치 합계는 반드시 1.0이어야 한다
(risk_engine.py가 로드 시점에 검증한다).
"""

MODEL_VERSION = "rule+ml-v2"

# ── 카테고리 가중치 (합계 1.0) ────────────────────────────────────────────
CATEGORY_WEIGHTS: dict[str, float] = {
    "price_volatility": 0.25,  # 가격변동성
    "liquidity": 0.20,  # 유동성
    "regional_supply": 0.15,  # 지역공급
    "property_risk": 0.25,  # 물건리스크
    "policy_risk": 0.15,  # 정책리스크
}

CATEGORY_LABELS: dict[str, str] = {
    "price_volatility": "가격변동성",
    "liquidity": "유동성",
    "regional_supply": "지역공급",
    "property_risk": "물건리스크",
    "policy_risk": "정책리스크",
}

# ── 카테고리 내부 지표 가중치 (각 카테고리별 합계 1.0) ───────────────────
INDICATOR_WEIGHTS: dict[str, dict[str, float]] = {
    "price_volatility": {"price_cv": 0.6, "jeonse_ratio": 0.4},
    "liquidity": {"volume_change": 0.5, "auction_ratio": 0.5},
    "regional_supply": {"unsold_units": 0.5, "population_change": 0.5},
    "property_risk": {"building_age": 0.3, "mortgage_ratio": 0.5, "land_value": 0.2},
    "policy_risk": {"regulation_zone": 1.0},
}

INDICATOR_LABELS: dict[str, str] = {
    "price_cv": "실거래가 변동계수(12개월)",
    "jeonse_ratio": "전세가율",
    "volume_change": "거래량 증감률",
    "auction_ratio": "낙찰가율 추이",
    "unsold_units": "미분양 현황",
    "population_change": "인구 증감률",
    "building_age": "건물 연식",
    "mortgage_ratio": "근저당 설정액 대비 시세비율",
    "land_value": "토지가치평가(개발잠재력·입지가치)",
    "regulation_zone": "규제지역 LTV 한도",
}

# 최종 등급(상/중/하) 컷오프 — 종합점수(0~100, 높을수록 고위험) 기준
GRADE_TIER_THRESHOLDS: dict[str, float] = {"low_max": 33.0, "medium_max": 66.0}
GRADE_TIER_LABELS: dict[str, str] = {"low": "하", "medium": "중", "high": "상"}

# ── 낙찰가율 추이 더미 데이터 (%, 100에 가까울수록 안정적) — 공식 API 없음 ──
DUMMY_AUCTION_PRICE_RATIO: dict[str, float] = {
    "강남구": 92.0,
    "서초구": 91.5,
    "마포구": 88.0,
    "성남시 분당구": 89.0,
    "수원시 영통구": 85.0,
}
DEFAULT_AUCTION_PRICE_RATIO = 82.0

# ── 지역공급 더미 데이터 (요구사항: "샘플 데이터로 우선 구현") ─────────────
DUMMY_UNSOLD_UNITS: dict[str, int] = {  # 시군구 미분양 세대수
    "강남구": 15,
    "서초구": 20,
    "마포구": 80,
    "성남시 분당구": 40,
    "수원시 영통구": 150,
}
DEFAULT_UNSOLD_UNITS = 200

DUMMY_POPULATION_CHANGE_PCT: dict[str, float] = {  # 최근 1년 인구증감률(%)
    "강남구": -0.3,
    "서초구": 0.1,
    "마포구": -0.5,
    "성남시 분당구": -0.8,
    "수원시 영통구": 1.2,
}
DEFAULT_POPULATION_CHANGE_PCT = -1.0

# ── 정책리스크: 규제지역 더미 데이터 (구분, LTV 한도 %) ────────────────────
REGULATION_ZONES: dict[str, tuple[str, int]] = {
    "강남구": ("투기과열지구", 40),
    "서초구": ("투기과열지구", 40),
    "마포구": ("조정대상지역", 50),
    "성남시 분당구": ("조정대상지역", 50),
    "수원시 영통구": ("비규제지역", 70),
}
DEFAULT_REGULATION_ZONE: tuple[str, int] = ("비규제지역", 70)


def validate_config() -> None:
    total = round(sum(CATEGORY_WEIGHTS.values()), 6)
    if total != 1.0:
        raise ValueError(f"CATEGORY_WEIGHTS 합계는 1.0이어야 합니다 (현재 {total}).")
    for category, weights in INDICATOR_WEIGHTS.items():
        subtotal = round(sum(weights.values()), 6)
        if subtotal != 1.0:
            raise ValueError(f"INDICATOR_WEIGHTS['{category}'] 합계는 1.0이어야 합니다 (현재 {subtotal}).")


validate_config()
