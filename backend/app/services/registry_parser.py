"""등기부등본 텍스트에서 갑구/을구 권리사항을 규칙 기반으로 파싱한다.

PDF에서 추출한 텍스트는 표 구조(순위번호/등기목적/접수/등기원인/권리자 및 기타사항 컬럼)가
깨진 채로 한 줄에 이어지는 경우가 많아, 컬럼 단위 파싱 대신 권리유형 키워드를 기준으로
주변 텍스트 구간(윈도우)을 잘라 채권최고액·권리자·등기일자를 정규식으로 추출하는 방식을 쓴다.
표 형식이 표준과 다른 문서에서는 일부 항목이 누락될 수 있어 raw_text(원문 일부)를 항상 함께
반환해 심사역이 원문을 직접 대조할 수 있게 한다 — 프로토타입 단계의 의도된 한계다.
"""

import re

from app.schemas.registry import RegistryRight

SECTION_PATTERN = re.compile(r"갑\s*구|을\s*구")

RIGHT_TYPE_KEYWORDS = [
    "소유권보존",
    "소유권이전청구권가등기",
    "소유권이전",
    "근저당권설정",
    "근저당권변경",
    "근저당권말소",
    "전세권설정",
    "지상권설정",
    "임차권설정",
    "가압류",
    "가처분",
    "가등기",
    "압류",
    "임의경매개시결정",
    "강제경매개시결정",
    "환매특약",
]

WINDOW_SIZE = 300
AMOUNT_PATTERN = re.compile(r"금\s*([0-9][0-9,]*)\s*원")
DATE_PATTERN = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")
HOLDER_PATTERN = re.compile(
    r"(?:근저당권자|전세권자|지상권자|채권자|권리자|임차권자)\s*[:：]?\s*([^\n,()]{2,20})"
)

# 길이가 긴 키워드를 먼저 두어 "가압류" 안에 "압류"가 부분매칭되는 것을 방지한다.
# 하나의 정규식으로 finditer를 돌리면 이미 매칭된 구간은 다시 스캔하지 않으므로
# (가압류 3글자를 매칭하고 나면 그 내부의 "압류"는 애초에 시작 지점이 없다) 겹침이 원천적으로 없다.
KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in sorted(RIGHT_TYPE_KEYWORDS, key=len, reverse=True))
)

CANCELLATION_MARKERS = ("말소", "해지")

RISK_KEYWORDS = {
    "가압류": "가압류 등기가 존재합니다 — 소유권 이전 및 대출 실행에 제약이 있을 수 있습니다.",
    "가처분": "가처분 등기가 존재합니다 — 소유권 이전 및 대출 실행에 제약이 있을 수 있습니다.",
    "압류": "압류 등기가 존재합니다 — 세금 체납 등의 사유일 수 있어 확인이 필요합니다.",
    "가등기": "가등기가 존재합니다 — 향후 본등기 시 후순위 권리가 소멸될 위험이 있습니다.",
    "임의경매개시결정": "경매개시결정 등기가 존재합니다 — 담보권 실행 절차가 진행 중일 수 있어 긴급 확인이 필요합니다.",
    "강제경매개시결정": "경매개시결정 등기가 존재합니다 — 채권자의 강제집행 절차가 진행 중일 수 있어 긴급 확인이 필요합니다.",
}


def _split_sections(text: str) -> dict[str, str]:
    markers = list(SECTION_PATTERN.finditer(text))
    sections: dict[str, str] = {}

    for i, marker in enumerate(markers):
        label = "갑구" if "갑" in marker.group() else "을구"
        start = marker.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        # 같은 라벨이 여러 번 매칭될 수 있어(페이지 헤더 반복 등) 가장 긴 구간을 채택한다
        chunk = text[start:end]
        if label not in sections or len(chunk) > len(sections[label]):
            sections[label] = chunk

    return sections


def _parse_amount(window: str) -> int | None:
    match = AMOUNT_PATTERN.search(window)
    if not match:
        return None
    won = int(match.group(1).replace(",", ""))
    return round(won / 10000)  # 만원 단위로 통일


def _parse_date(window: str) -> str | None:
    match = DATE_PATTERN.search(window)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _parse_holder(window: str) -> str | None:
    match = HOLDER_PATTERN.search(window)
    if not match:
        return None
    # 컬럼 사이 넓은 공백(2칸 이상)을 다음 항목과의 경계로 보고 첫 구간만 사용한다.
    holder = re.split(r"\s{2,}", match.group(1).strip())[0].strip()
    return holder or None


def _filter_narrative_matches(section_text: str, matches: list[re.Match]) -> list[re.Match]:
    """"OO법원의 가압류결정" 같은 등기원인 서술 속 키워드는 새 권리사항이 아니라
    이미 발견된 항목의 부연설명이므로 제외한다 (등기목적 컬럼의 독립 키워드만 남긴다)."""

    filtered = []
    for m in matches:
        if m.group() in ("가압류", "가처분", "압류") and section_text[m.end() : m.end() + 2] == "결정":
            continue
        filtered.append(m)
    return filtered


def _parse_section(section_label: str, section_text: str) -> list[RegistryRight]:
    matches = _filter_narrative_matches(section_text, list(KEYWORD_PATTERN.finditer(section_text)))

    entries: list[RegistryRight] = []
    seen: set[tuple[str, int | None, str | None]] = set()

    for i, m in enumerate(matches):
        right_type = m.group()
        # 윈도우가 다음에 감지된 권리사항의 시작 지점을 넘지 않게 해 항목 간 필드 혼입을 막는다.
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        window_end = min(m.start() + WINDOW_SIZE, next_start)
        window = section_text[m.start() : window_end]

        amount = _parse_amount(window)
        holder = _parse_holder(window)
        dedup_key = (right_type, amount, holder)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        entries.append(
            RegistryRight(
                section=section_label,
                rank=None,  # PDF 텍스트 추출 시 표 구조가 깨져 순위번호는 신뢰도가 낮아 생략
                right_type=right_type,
                holder=holder,
                amount=amount,
                registered_date=_parse_date(window),
                raw_text=" ".join(window.split())[:200],
            )
        )

    return entries


def parse_rights(text: str) -> list[RegistryRight]:
    sections = _split_sections(text)
    rights: list[RegistryRight] = []
    for label, section_text in sections.items():
        rights.extend(_parse_section(label, section_text))
    return rights


def compute_mortgage_total(rights: list[RegistryRight]) -> int:
    """근저당권설정 채권최고액 합계 (만원). 말소 여부는 파싱 단계에서 구분하지 않으므로
    현재 유효한 근저당권만 반영하지는 못한다 — raw_text로 심사역이 대조할 수 있게 해둔다."""

    return sum(r.amount for r in rights if r.right_type.startswith("근저당권설정") and r.amount is not None)


def detect_risk_flags(rights: list[RegistryRight], estimated_price: int | None = None) -> list[str]:
    flags: list[str] = []
    present_types = {r.right_type for r in rights}

    for keyword, message in RISK_KEYWORDS.items():
        if keyword in present_types:
            flags.append(message)

    mortgage_total = compute_mortgage_total(rights)
    if mortgage_total > 0:
        flags.append(f"근저당권 채권최고액 합계 약 {mortgage_total:,}만원")
        if estimated_price and estimated_price > 0:
            ratio = mortgage_total / estimated_price
            if ratio >= 0.7:
                flags.append(f"근저당권 합계가 AI 추정시세의 {ratio:.0%}에 달해 담보여력이 부족할 수 있습니다.")

    if not flags:
        flags.append("주요 위험 권리사항이 발견되지 않았습니다.")

    return flags
