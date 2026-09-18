"""권리분석 결과를 심사역용 자연어 요약으로 변환한다.

ANTHROPIC_API_KEY가 설정돼 있으면 Claude API로 권리관계 요약·투자가치 판단·리스크 설명을
생성하고(개발요건서 기능2), 키가 없거나 호출에 실패하면 파싱 결과를 그대로 문장으로 조립하는
템플릿 기반 요약으로 자동 폴백한다.
"""

import logging
from collections import Counter

from app.core.config import settings
from app.schemas.registry import RegistryRight

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "당신은 금융회사 담보대출 심사역을 보조하는 등기부등본 분석 보조원입니다. "
    "제공된 파싱 결과만 근거로 답하고, 확정적 단정("
    "'문제없습니다' 등) 대신 필요한 경우 추가 확인을 권고하는 신중한 어조를 사용하세요."
)


def _template_summary(rights: list[RegistryRight], risk_flags: list[str]) -> str:
    gap_count = sum(1 for r in rights if r.section == "갑구")
    eul_count = sum(1 for r in rights if r.section == "을구")
    type_counts = Counter(r.right_type for r in rights)
    type_summary = ", ".join(f"{t} {c}건" for t, c in type_counts.items())

    lines = [
        f"등기부등본 분석 결과 갑구 {gap_count}건, 을구 {eul_count}건의 권리사항이 확인되었습니다.",
        f"확인된 권리유형: {type_summary}." if type_summary else "권리유형을 특정하지 못했습니다.",
        "리스크 요인: " + " / ".join(risk_flags),
    ]
    return "\n".join(lines)


def _build_prompt(rights: list[RegistryRight], risk_flags: list[str], property_context: str | None) -> str:
    if rights:
        rights_desc = "\n".join(
            f"- [{r.section}] {r.right_type} / 권리자: {r.holder or '미상'} / "
            f"금액: {r.amount if r.amount is not None else '-'}만원 / 등기일: {r.registered_date or '미상'}"
            for r in rights
        )
    else:
        rights_desc = "확인된 권리사항 없음"

    flags_desc = "\n".join(f"- {f}" for f in risk_flags)
    context_line = f"\n물건 정보: {property_context}" if property_context else ""

    return (
        "다음은 등기부등본에서 자동 파싱된 권리사항 목록입니다.\n"
        f"{rights_desc}\n\n"
        f"감지된 리스크 요인:\n{flags_desc}\n"
        f"{context_line}\n\n"
        "위 정보를 바탕으로 담보대출 심사역이 참고할 권리관계 요약, 투자가치 판단, 리스크 요인 설명을 "
        "3~5문장의 한국어 평문으로 작성해주세요."
    )


def _llm_summary(rights: list[RegistryRight], risk_flags: list[str], property_context: str | None) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(rights, risk_flags, property_context)}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def generate_summary(
    rights: list[RegistryRight],
    risk_flags: list[str],
    property_context: str | None = None,
) -> tuple[str, str]:
    if settings.ANTHROPIC_API_KEY:
        try:
            return _llm_summary(rights, risk_flags, property_context), "llm"
        except Exception:
            logger.exception("Claude API 권리분석 요약 생성 실패, 템플릿으로 폴백합니다.")

    return _template_summary(rights, risk_flags), "template"
