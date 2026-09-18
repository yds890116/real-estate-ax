"""유사 감정평가·거래사례 검색(RAG) — 구조화된 메타데이터(지역·용도·면적) 기반 검색(R) +
Claude API 기반 참고 감정가·판단근거 설명 생성(G)으로 구성한다.

임베딩 기반 유사도 대신 지역/용도/면적을 규칙으로 스코어링하는 이유: appraisal_cases의
필드가 이미 정형화돼 있어 각 축의 기여도를 심사역에게 그대로 설명할 수 있고(투명성),
샘플 데이터 규모(수십 건)에서는 벡터DB 도입 효과가 크지 않기 때문이다.

1순위로 분석 대상과 같은 단지의 실거래가(최근 3개월)를 우선 사용한다 — appraisal_cases
표본(감정평가서 2건에서 파싱한 20건 남짓)은 규모가 작고 지역도 강남 일부에 한정돼 있어,
전혀 다른 단지와 비교되며 AI 추정시세와 참고 감정가 사이에 괴리가 크게 나는 문제가 있었다.
같은 단지의 실거래가 쪽이 훨씬 신뢰도가 높으므로, 구할 수 있으면 이를 우선하고 없을 때만
appraisal_cases 기반 검색으로 폴백한다.
"""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appraisal_case import AppraisalCase
from app.models.market_transaction import MarketTransaction
from app.schemas.appraisal import AppraisalCaseResponse, AppraisalSearchResult
from app.schemas.market_data import MarketTransactionResponse
from app.schemas.property import PropertyBase
from app.services.external.kakao_client import KakaoApiError
from app.services.external.molit_client import MolitApiError
from app.services.market_search import name_matches, search_market_transactions

logger = logging.getLogger(__name__)

REAL_TXN_MONTHS = 3
SAME_TIER_TOLERANCE_SQM = 1.0  # 같은 평형으로 간주할 전용면적 오차 허용범위(㎡)

USAGE_EQUIVALENTS: dict[str, set[str]] = {
    "아파트": {"아파트", "공동주택(아파트)"},
    "오피스텔": {"오피스텔"},
    "도시형생활주택": {"도시형생활주택"},
    "근린생활시설": {"근린생활시설"},
}

REGION_WEIGHT = 0.5
USAGE_WEIGHT = 0.3
AREA_WEIGHT = 0.2

SYSTEM_PROMPT = (
    "당신은 금융회사 담보대출 심사역을 보조하는 감정평가 참고자료 분석 보조원입니다. "
    "제공된 유사사례만 근거로 답하고, 감정평가는 감정평가사의 고유 업무이므로 "
    "확정적 단정 대신 참고용임을 분명히 하는 신중한 어조를 사용하세요."
)


def _usage_score(query_usage: str, case_usage: str) -> float:
    if query_usage == case_usage:
        return 1.0
    group = USAGE_EQUIVALENTS.get(query_usage)
    if group and case_usage in group:
        return 1.0
    return 0.0


def _region_score(prop: PropertyBase, case: AppraisalCase) -> float:
    if case.sigungu == prop.sigungu and case.sido == prop.sido:
        score = 1.0
        if case.dong and prop.dong and case.dong == prop.dong:
            score = 1.0  # 동까지 일치해도 상한은 1.0 (가중치는 area/usage에서 구분)
        return score
    if case.sido == prop.sido:
        return 0.4
    return 0.0


def _area_score(query_area: float, case_area: float) -> float:
    if query_area <= 0:
        return 0.0
    diff_ratio = abs(case_area - query_area) / query_area
    return max(0.0, 1 - diff_ratio)


def _rank_cases(db: Session, prop: PropertyBase, usage: str, exclusive_area: float, top_k: int) -> list[tuple[AppraisalCase, float]]:
    all_cases = db.query(AppraisalCase).all()
    scored = []
    for case in all_cases:
        score = (
            REGION_WEIGHT * _region_score(prop, case)
            + USAGE_WEIGHT * _usage_score(usage, case.usage)
            + AREA_WEIGHT * _area_score(exclusive_area, case.exclusive_area)
        )
        if score > 0:
            scored.append((case, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def _reference_price_per_area(ranked: list[tuple[AppraisalCase, float]]) -> int | None:
    weight_sum = sum(score for _, score in ranked)
    if weight_sum == 0:
        return None
    weighted_unit_price = sum(case.unit_price * score for case, score in ranked) / weight_sum
    return round(weighted_unit_price)


def _template_explanation(ranked: list[tuple[AppraisalCase, float]], reference_price_per_area: int | None) -> str:
    if not ranked:
        return "유사사례를 찾지 못했습니다. 현재 표본 데이터가 부족하거나 지역/용도가 일치하는 사례가 없습니다."

    top = ranked[0][0]
    lines = [
        f"유사사례 {len(ranked)}건을 검색했으며, 유사도가 가장 높은 사례는 "
        f"{top.dong} '{top.complex_name}'({top.usage}, {top.exclusive_area}㎡)입니다.",
    ]
    if reference_price_per_area:
        lines.append(f"유사사례 가중평균 단가는 약 {reference_price_per_area:,}만원/㎡입니다.")
    case_types = {case.case_type for case, _ in ranked}
    if "감정평가사례" in case_types:
        lines.append("감정평가사례가 포함되어 있어 실제 감정평가 관행을 참고할 수 있습니다.")
    return " ".join(lines)


def _build_prompt(prop: PropertyBase, ranked: list[tuple[AppraisalCase, float]], reference_price_per_area: int | None) -> str:
    cases_desc = "\n".join(
        f"- [{case.case_type}] {case.dong} {case.complex_name} {case.dong_ho or ''} / {case.usage} / "
        f"{case.exclusive_area}㎡ / {case.event_date} / 단가 {case.unit_price:,}만원/㎡ (유사도 {score:.2f})"
        for case, score in ranked
    ) or "검색된 유사사례 없음"

    return (
        f"대상 물건: {prop.sido} {prop.sigungu} {prop.dong or ''}, 용도 {prop.property_type}, "
        f"전용면적 {prop.exclusive_area}㎡\n\n"
        f"검색된 유사 거래·감정평가 사례:\n{cases_desc}\n\n"
        f"유사사례 가중평균 단가: {f'{reference_price_per_area:,}만원/㎡' if reference_price_per_area else '산출 불가'}\n\n"
        "위 유사사례를 근거로 대상 물건의 참고 감정가에 대한 판단과 그 근거를 3~5문장의 한국어 평문으로 "
        "작성해주세요. 감정평가는 감정평가사의 고유 업무이므로 참고용임을 분명히 해주세요."
    )


def _llm_explanation(prop: PropertyBase, ranked: list[tuple[AppraisalCase, float]], reference_price_per_area: int | None) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(prop, ranked, reference_price_per_area)}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _local_complex_transactions(db: Session, prop: PropertyBase) -> list[MarketTransaction]:
    """market_transactions에 이미 적재된 같은 단지 거래를 먼저 찾는다 (외부 API 재호출 방지).

    실거래가 검색(/market-data/search)에서 물건을 등록할 때 이미 해당 단지 데이터를 적재해두므로,
    분석 화면을 다시 열 때마다 카카오/국토부 API를 반복 호출하지 않도록 로컬 데이터를 우선 쓴다."""

    cutoff = (date.today() - timedelta(days=REAL_TXN_MONTHS * 31)).isoformat()
    rows = (
        db.query(MarketTransaction)
        .filter(MarketTransaction.sigungu == prop.sigungu, MarketTransaction.deal_date >= cutoff)
        .all()
    )
    return [r for r in rows if name_matches(prop.complex_name or "", r.complex_name)]


def _search_real_transactions(db: Session, prop: PropertyBase) -> AppraisalSearchResult | None:
    """같은 단지의 최근 실거래가 중 가장 작은 평형을 기본값으로 삼아 참고 시세를 구성한다."""

    if not prop.complex_name:
        return None

    local_rows = _local_complex_transactions(db, prop)
    if local_rows:
        sale_txns = [MarketTransactionResponse.model_validate(r) for r in local_rows]
    else:
        query = f"{prop.sido} {prop.sigungu} {prop.complex_name}"
        try:
            search_result = search_market_transactions(db, query, months=REAL_TXN_MONTHS)
        except (KakaoApiError, MolitApiError):
            logger.warning("단지 실거래가 조회 실패, appraisal_cases 검색으로 폴백합니다: %s", query)
            return None
        sale_txns = search_result.sale.transactions

    if not sale_txns:
        return None

    reference_area = min(t.exclusive_area for t in sale_txns)
    tier_txns = sorted(
        (t for t in sale_txns if abs(t.exclusive_area - reference_area) <= SAME_TIER_TOLERANCE_SQM),
        key=lambda t: t.deal_date,
        reverse=True,
    )

    unit_prices = [t.deal_price / t.exclusive_area for t in tier_txns]
    reference_price_per_area = round(sum(unit_prices) / len(unit_prices))
    reference_price = round(sum(t.deal_price for t in tier_txns) / len(tier_txns))

    cases = [
        AppraisalCaseResponse(
            id=t.id,
            source_file=f"국토교통부 실거래가 ({t.deal_date[:7]})",
            case_type="실거래",
            sido=t.sido,
            sigungu=t.sigungu,
            dong=t.dong,
            jibun=None,
            complex_name=t.complex_name or prop.complex_name,
            dong_ho=f"{t.floor}층" if t.floor is not None else None,
            usage="아파트",
            exclusive_area=t.exclusive_area,
            event_date=t.deal_date,
            purpose=None,
            amount=t.deal_price,
            unit_price=round(t.deal_price / t.exclusive_area),
            location_note=None,
            approval_date=str(t.build_year) if t.build_year else None,
            similarity=1.0,
        )
        for t in tier_txns
    ]

    explanation = (
        f"'{prop.complex_name}' 단지의 최근 {REAL_TXN_MONTHS}개월 실거래가를 조회한 결과, 거래된 평형 중 "
        f"가장 작은 {reference_area:.2f}㎡ 타입을 기본 비교군으로 삼았습니다 (총 {len(tier_txns)}건). "
        f"해당 평형의 평균 실거래가는 {reference_price:,}만원(단가 {reference_price_per_area:,}만원/㎡)입니다. "
        f"동일 단지의 실제 거래이므로 AI 추정시세·유사감정사례 대비 참고 신뢰도가 높으나, 분석 대상과 "
        f"평형이 다를 수 있어 절대 가격이 아닌 단가 기준으로 비교하시길 권장합니다."
    )

    return AppraisalSearchResult(
        cases=cases,
        reference_price_per_area=reference_price_per_area,
        reference_price=reference_price,
        reference_area=reference_area,
        explanation=explanation,
        generation_method="template",
    )


def search_similar_cases(
    db: Session,
    prop: PropertyBase,
    usage: str | None = None,
    top_k: int = 5,
) -> AppraisalSearchResult:
    real_result = _search_real_transactions(db, prop)
    if real_result is not None:
        return real_result

    query_usage = usage or prop.property_type
    ranked = _rank_cases(db, prop, query_usage, prop.exclusive_area, top_k)

    reference_price_per_area = _reference_price_per_area(ranked)
    reference_price = round(reference_price_per_area * prop.exclusive_area) if reference_price_per_area else None

    if settings.ANTHROPIC_API_KEY:
        try:
            explanation = _llm_explanation(prop, ranked, reference_price_per_area)
            generation_method = "llm"
        except Exception:
            logger.exception("Claude API 유사사례 설명 생성 실패, 템플릿으로 폴백합니다.")
            explanation = _template_explanation(ranked, reference_price_per_area)
            generation_method = "template"
    else:
        explanation = _template_explanation(ranked, reference_price_per_area)
        generation_method = "template"

    cases_response = []
    for case, score in ranked:
        resp = AppraisalCaseResponse.model_validate(case)
        resp.similarity = round(score, 3)
        cases_response.append(resp)

    return AppraisalSearchResult(
        cases=cases_response,
        reference_price_per_area=reference_price_per_area,
        reference_price=reference_price,
        explanation=explanation,
        generation_method=generation_method,
    )
