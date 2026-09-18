"""담보 리스크 스코어링 엔진 v2 (규칙 + ML 하이브리드).

5개 카테고리(가격변동성/유동성/지역공급/물건리스크/정책리스크)로 지표를 묶고, 각 지표를
0~100(높을수록 고위험)으로 정규화한 뒤 app/core/risk_config.py의 가중치로 가중합해 종합점수를
산출한다. 가중치·기준값은 전부 risk_config.py에 분리돼 있어 이 파일을 건드리지 않고도
조정할 수 있다.

- 가격변동성: 최근 12개월 실거래가 변동계수(ML, 회귀 없이 직접 계산) + 전세가율
- 유동성: 거래량 증감률 + 낙찰가율 추이(더미)
- 지역공급: 미분양 현황 + 인구 증감 (샘플 데이터로 우선 구현)
- 물건리스크: 건축연수 + 근저당 설정액 대비 시세비율(등기부 연동)
- 정책리스크: 규제지역 여부에 따른 LTV 한도(더미)

최종 등급은 기존 1~10 등급(risk_grade)·5단계 라벨(risk_level_label)을 유지해 대시보드/
심사의견 등 기존 소비자가 그대로 동작하게 하고, v2에서 요구된 3단계 등급(상/중/하)은
grade_tier로 추가 제공한다. 카테고리·지표별 기여도는 categories에 담아 화면에서 breakdown을
보여줄 수 있게 한다.
"""

from sqlalchemy.orm import Session

from app.core.risk_config import CATEGORY_LABELS, CATEGORY_WEIGHTS, GRADE_TIER_THRESHOLDS, INDICATOR_LABELS, INDICATOR_WEIGHTS, MODEL_VERSION
from app.schemas.property import PropertyBase
from app.schemas.risk import RiskCategory, RiskFactor, RiskIndicator, RiskScoreResult
from app.schemas.valuation import ValuationResult
from app.services import risk_indicators as ind

RISK_LEVEL_LABELS = {
    range(1, 3): "안전",
    range(3, 5): "양호",
    range(5, 7): "주의",
    range(7, 9): "위험",
    range(9, 11): "고위험",
}


def _grade_label(grade: int) -> str:
    for grade_range, label in RISK_LEVEL_LABELS.items():
        if grade in grade_range:
            return label
    return "미분류"


def _grade_tier(score: float) -> str:
    if score <= GRADE_TIER_THRESHOLDS["low_max"]:
        return "하"
    if score <= GRADE_TIER_THRESHOLDS["medium_max"]:
        return "중"
    return "상"


class RiskEngine:
    def score(
        self,
        prop: PropertyBase,
        valuation: ValuationResult,
        db: Session,
        mortgage_total: int | None = None,
    ) -> RiskScoreResult:
        raw_indicators: dict[str, tuple[str, float, str]] = {
            "price_cv": ind.price_volatility_cv(db, prop.sigungu),
            "jeonse_ratio": ind.jeonse_ratio(db, prop.sigungu),
            "volume_change": ind.volume_change(db, prop.sigungu),
            "auction_ratio": ind.auction_price_ratio(prop.sigungu),
            "unsold_units": ind.unsold_units(prop.sigungu),
            "population_change": ind.population_change(prop.sigungu),
            "building_age": ind.building_age(prop.build_year),
            "mortgage_ratio": ind.mortgage_ratio(mortgage_total, valuation.estimated_price),
            "regulation_zone": ind.regulation_zone(prop.sigungu),
        }

        categories: list[RiskCategory] = []
        factors: list[RiskFactor] = []
        total_score = 0.0

        for cat_key, cat_weight in CATEGORY_WEIGHTS.items():
            indicator_weights = INDICATOR_WEIGHTS[cat_key]
            indicators: list[RiskIndicator] = []
            cat_score = 0.0

            for ind_key, ind_weight in indicator_weights.items():
                description, normalized_score, method = raw_indicators[ind_key]
                indicators.append(
                    RiskIndicator(
                        key=ind_key,
                        label=INDICATOR_LABELS[ind_key],
                        description=description,
                        normalized_score=round(normalized_score, 1),
                        weight=ind_weight,
                        method=method,
                        available="부족" not in description and "미확인" not in description and "없음" not in description,
                    )
                )
                cat_score += normalized_score * ind_weight

            contribution = cat_score * cat_weight
            total_score += contribution

            categories.append(
                RiskCategory(
                    key=cat_key,
                    label=CATEGORY_LABELS[cat_key],
                    weight=cat_weight,
                    normalized_score=round(cat_score, 1),
                    contribution=round(contribution, 1),
                    indicators=indicators,
                )
            )

            cat_method = "ml" if any(i.method == "ml" for i in indicators) else "rule"
            factors.append(
                RiskFactor(
                    name=CATEGORY_LABELS[cat_key],
                    description=" / ".join(i.description for i in indicators),
                    impact="negative" if cat_score >= 50 else "positive",
                    weight=round(contribution, 1),
                    method=cat_method,
                )
            )

        total_score = min(100.0, max(0.0, total_score))
        risk_grade = max(1, min(10, round(total_score / 10) or 1))

        return RiskScoreResult(
            risk_grade=risk_grade,
            risk_level_label=_grade_label(risk_grade),
            grade_tier=_grade_tier(total_score),
            score=round(total_score, 1),
            model_version=MODEL_VERSION,
            categories=categories,
            factors=factors,
        )


risk_engine = RiskEngine()
