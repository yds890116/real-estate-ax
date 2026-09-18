"""기능1(시세·리스크)~기능3(유사사례)와 등기부 권리분석(있는 경우)을 종합해
표준 양식 심사의견서 초안을 생성한다 (개발요건서 "통합 기능").

ANTHROPIC_API_KEY가 있으면 Claude API로 자연스러운 문장의 심사의견을 생성하고,
없으면 각 기능 결과를 그대로 조립하는 템플릿으로 폴백한다 (기능2/3과 동일한 패턴).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opinion import ReviewOpinion
from app.models.property import Property
from app.models.registry_analysis import RegistryAnalysis
from app.schemas.property import PropertyBase
from app.services.appraisal_search import search_similar_cases
from app.services.risk_engine import risk_engine
from app.services.valuation_engine import valuation_engine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "당신은 금융회사 담보대출 심사역을 보조하는 심사의견 초안 작성 보조원입니다. "
    "제공된 시세·리스크·권리관계·유사사례 분석 결과만 근거로 표준 심사의견서를 작성하세요. "
    "이 의견은 심사역이 검토·수정할 초안이므로 확정적 승인/거절 표현은 피하고, "
    "'■ 물건개요', '■ 시세분석', '■ 담보 리스크 평가', '■ 권리관계', '■ 유사 감정사례 참고', "
    "'■ 종합의견' 6개 섹션 제목을 그대로 사용해 한국어로 작성하세요."
)


class OpinionNotFoundError(Exception):
    pass


def _collect_context(db: Session, property_id: int):
    db_property = db.get(Property, property_id)
    if db_property is None:
        raise ValueError("Property not found")

    prop = PropertyBase.model_validate(db_property)
    valuation = valuation_engine.estimate(prop, db)
    risk = risk_engine.score(prop, valuation)
    registry = (
        db.query(RegistryAnalysis)
        .filter(RegistryAnalysis.property_id == property_id)
        .order_by(RegistryAnalysis.created_at.desc())
        .first()
    )
    appraisal = search_similar_cases(db, prop, usage=prop.property_type)

    return db_property, prop, valuation, risk, registry, appraisal


def _overall_judgement(risk_grade: int, registry: RegistryAnalysis | None) -> str:
    registry_issue = bool(
        registry and registry.risk_flags and registry.risk_flags != ["주요 위험 권리사항이 발견되지 않았습니다."]
    )

    if risk_grade >= 7 or registry_issue:
        return (
            "리스크 등급 또는 권리관계상 주의가 필요한 사항이 확인되었습니다. "
            "담보 취득 전 관련 사항에 대한 면밀한 검토가 필요합니다."
        )
    if risk_grade >= 5:
        return "리스크 등급이 주의 수준으로, 관련 요인에 대한 추가 확인 후 심사를 진행하는 것이 바람직합니다."
    return (
        "전반적으로 안정적인 담보가치와 리스크 수준을 보이며, 현재까지 확인된 정보상 "
        "특별한 제약 사항은 발견되지 않았습니다. 통상적인 심사 절차에 따라 진행 가능할 것으로 판단됩니다."
    )


def _template_opinion(db_property: Property, valuation, risk, registry, appraisal) -> str:
    factor_lines = "\n".join(
        f"  - {f.name}({f.weight:.1f}점 기여): {f.description}" for f in risk.factors
    ) or "  - 산출된 카테고리 없음"

    if registry is not None:
        registry_block = (
            f"- 업로드 파일: {registry.filename}\n"
            f"- 요약: {registry.summary}\n"
            f"- 리스크 요인: {', '.join(registry.risk_flags)}"
        )
    else:
        registry_block = "- 등기부등본이 업로드되지 않아 권리관계를 확인하지 못했습니다. 업로드 후 재생성을 권장합니다."

    if appraisal.reference_price is not None:
        appraisal_block = (
            f"- 참고 감정가: {appraisal.reference_price:,}만원 (단가 {appraisal.reference_price_per_area:,}만원/㎡ 기준)\n"
            f"- {appraisal.explanation}"
        )
    else:
        appraisal_block = "- 조건에 맞는 유사사례를 찾지 못했습니다."

    return f"""■ 물건개요
- 소재지: {db_property.address}
- 용도/면적: {db_property.property_type}, 전용 {db_property.exclusive_area}㎡ (준공 {db_property.build_year or '미상'}년)
- 단지규모: {db_property.household_count or '미상'}세대

■ 시세분석
- AI 추정시세: {valuation.estimated_price:,}만원 (범위 {valuation.price_lower:,}~{valuation.price_upper:,}만원, 신뢰도 {round(valuation.confidence_level * 100)}%)
- 비교사례 {valuation.comparable_count}건, 모델: {valuation.model_version}

■ 담보 리스크 평가
- 리스크 등급: {risk.risk_grade}등급 ({risk.risk_level_label}, 종합판정 {risk.grade_tier}), 종합점수 {risk.score}/100
- 카테고리별 평가:
{factor_lines}

■ 권리관계
{registry_block}

■ 유사 감정사례 참고
{appraisal_block}

■ 종합의견
{_overall_judgement(risk.risk_grade, registry)}
"""


def _build_llm_prompt(db_property: Property, valuation, risk, registry, appraisal) -> str:
    factors_desc = "\n".join(f"- {f.name}({f.method}): {f.description}" for f in risk.factors)
    registry_desc = (
        f"요약: {registry.summary}\n리스크요인: {', '.join(registry.risk_flags)}" if registry else "업로드되지 않음"
    )
    appraisal_desc = (
        f"참고감정가 {appraisal.reference_price:,}만원, 설명: {appraisal.explanation}"
        if appraisal.reference_price is not None
        else "유사사례 없음"
    )

    return f"""물건: {db_property.address}, {db_property.property_type} {db_property.exclusive_area}㎡, 준공 {db_property.build_year or '미상'}년, {db_property.household_count or '미상'}세대

[시세] 추정 {valuation.estimated_price:,}만원 (범위 {valuation.price_lower:,}~{valuation.price_upper:,}만원, 신뢰도 {valuation.confidence_level})
[리스크] {risk.risk_grade}등급({risk.risk_level_label}), 점수 {risk.score}
{factors_desc}
[권리관계] {registry_desc}
[유사사례] {appraisal_desc}

위 정보를 바탕으로 6개 섹션(물건개요/시세분석/담보 리스크 평가/권리관계/유사 감정사례 참고/종합의견)으로 구성된 심사의견서 초안을 작성해주세요."""


def _generate_content(db_property: Property, valuation, risk, registry, appraisal) -> tuple[str, str]:
    if settings.ANTHROPIC_API_KEY:
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_llm_prompt(db_property, valuation, risk, registry, appraisal)}],
            )
            content = "".join(block.text for block in response.content if block.type == "text").strip()
            return content, "llm"
        except Exception:
            logger.exception("Claude API 심사의견 생성 실패, 템플릿으로 폴백합니다.")

    return _template_opinion(db_property, valuation, risk, registry, appraisal), "template"


def generate_opinion(db: Session, property_id: int) -> ReviewOpinion:
    db_property, prop, valuation, risk, registry, appraisal = _collect_context(db, property_id)
    content, method = _generate_content(db_property, valuation, risk, registry, appraisal)

    existing = db.query(ReviewOpinion).filter(ReviewOpinion.property_id == property_id).first()
    now_iso = datetime.now(timezone.utc).isoformat()

    if existing is not None:
        if existing.current_content != existing.ai_draft:
            history = list(existing.edit_history or [])
            history.append({"content": existing.current_content, "saved_at": existing.updated_at.isoformat()})
            existing.edit_history = history
        existing.ai_draft = content
        existing.current_content = content
        existing.generation_method = method
        db.commit()
        db.refresh(existing)
        return existing

    opinion = ReviewOpinion(
        property_id=property_id,
        ai_draft=content,
        current_content=content,
        edit_history=[],
        generation_method=method,
    )
    db.add(opinion)
    db.commit()
    db.refresh(opinion)
    return opinion


def get_opinion(db: Session, property_id: int) -> ReviewOpinion | None:
    return db.query(ReviewOpinion).filter(ReviewOpinion.property_id == property_id).first()


def update_opinion(db: Session, property_id: int, new_content: str) -> ReviewOpinion:
    opinion = get_opinion(db, property_id)
    if opinion is None:
        raise OpinionNotFoundError("아직 생성된 심사의견이 없습니다. 먼저 초안을 생성해주세요.")

    history = list(opinion.edit_history or [])
    history.append({"content": opinion.current_content, "saved_at": opinion.updated_at.isoformat()})
    opinion.edit_history = history
    opinion.current_content = new_content

    db.commit()
    db.refresh(opinion)
    return opinion
