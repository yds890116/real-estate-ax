"""포트폴리오 대시보드용 집계 — 등록된 물건 전체에 대해 기능1~3 결과를 요약하고
이상 매물(고위험/권리하자/시세 괴리)을 자동으로 표시한다.
"""

from sqlalchemy.orm import Session

from app.models.opinion import ReviewOpinion
from app.models.property import Property
from app.models.registry_analysis import RegistryAnalysis
from app.schemas.dashboard import DashboardItem
from app.schemas.property import PropertyBase
from app.schemas.registry import RegistryAnalysisResult
from app.services.appraisal_search import search_similar_cases
from app.services.registry_parser import compute_mortgage_total
from app.services.risk_engine import risk_engine
from app.services.valuation_engine import valuation_engine

RISK_ALERT_GRADE = 7
PRICE_GAP_ALERT_RATIO = 0.15
NO_REGISTRY_RISK_MESSAGE = "주요 위험 권리사항이 발견되지 않았습니다."


def _opinion_status(opinion: ReviewOpinion | None) -> str:
    if opinion is None:
        return "none"
    return "edited" if opinion.current_content != opinion.ai_draft else "draft"


def build_dashboard(db: Session) -> list[DashboardItem]:
    properties = db.query(Property).order_by(Property.created_at.desc()).all()
    items: list[DashboardItem] = []

    for db_property in properties:
        prop = PropertyBase.model_validate(db_property)
        valuation = valuation_engine.estimate(prop, db)

        registry = (
            db.query(RegistryAnalysis)
            .filter(RegistryAnalysis.property_id == db_property.id)
            .order_by(RegistryAnalysis.created_at.desc())
            .first()
        )
        registry_risk_count = 0
        mortgage_total = None
        if registry is not None:
            registry_risk_count = sum(1 for f in registry.risk_flags if f != NO_REGISTRY_RISK_MESSAGE)
            mortgage_total = compute_mortgage_total(RegistryAnalysisResult.model_validate(registry).rights) or None

        risk = risk_engine.score(prop, valuation, db, mortgage_total)

        appraisal = search_similar_cases(db, prop, usage=prop.property_type, top_k=5)
        price_gap_ratio = None
        if appraisal.reference_price is not None and valuation.estimated_price > 0:
            price_gap_ratio = (appraisal.reference_price - valuation.estimated_price) / valuation.estimated_price

        opinion = db.query(ReviewOpinion).filter(ReviewOpinion.property_id == db_property.id).first()

        alerts: list[str] = []
        if risk.risk_grade >= RISK_ALERT_GRADE:
            alerts.append(f"리스크 등급 {risk.risk_grade}({risk.risk_level_label})")
        if registry_risk_count > 0:
            alerts.append(f"등기부 권리상 위험요인 {registry_risk_count}건")
        if price_gap_ratio is not None and abs(price_gap_ratio) >= PRICE_GAP_ALERT_RATIO:
            direction = "높음" if price_gap_ratio > 0 else "낮음"
            alerts.append(f"유사감정사례 대비 AI시세 괴리 {abs(price_gap_ratio):.0%}({direction})")

        items.append(
            DashboardItem(
                property_id=db_property.id,
                address=db_property.address,
                sido=db_property.sido,
                sigungu=db_property.sigungu,
                property_type=db_property.property_type,
                exclusive_area=db_property.exclusive_area,
                estimated_price=valuation.estimated_price,
                price_per_area=valuation.price_per_area,
                risk_grade=risk.risk_grade,
                risk_level_label=risk.risk_level_label,
                has_registry=registry is not None,
                registry_risk_count=registry_risk_count,
                reference_price=appraisal.reference_price,
                price_gap_ratio=price_gap_ratio,
                opinion_status=_opinion_status(opinion),
                alerts=alerts,
                created_at=db_property.created_at,
            )
        )

    return items
