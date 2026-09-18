"""감정평가서 PDF에서 "거래사례"/"감정평가사례" 표를 규칙 기반으로 파싱한다.

감정평가서의 근거자료 표는 pypdf로 텍스트를 추출하면 한 항목이 여러 줄(소재지/명칭/동층호/
용도/면적/일자/금액/단가/비고)로 흩어져 나오고, 표 헤더가 셀을 넘나들며 줄바꿈되는 등 원본
표 구조가 깨진다. 이를 감안해 각 항목을 "기호+동"으로 시작하는 블록으로 나눈 뒤, 블록 전체를
한 줄로 합쳐 정규식으로 필드를 추출하는 방식을 쓴다. (등기부등본 파서와 동일한 접근.)
샘플 문서 2종 중 텍스트 레이어가 있는 1종을 기준으로 검증했으며, 표 형식이 다른 문서에서는
일부 행이 누락될 수 있다 — 프로토타입 단계의 의도된 한계다.
"""

import re
from dataclasses import dataclass

import pypdf

SIDO_NAMES = (
    "서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|"
    "세종특별자치시|경기도|강원특별자치도|충청북도|충청남도|전북특별자치도|전라남도|"
    "경상북도|경상남도|제주특별자치도"
)
SIDO_SIGUNGU_RE = re.compile(rf"({SIDO_NAMES})\s*([가-힣]+시\s+[가-힣]+구|[가-힣]+[구군시])")

SECTION_HEADING_RE = re.compile(r"\d+\.\s*(거래사례|감정평가사례)\b")
ROW_START_RE = re.compile(r"(?:^|\n)\s*([ㄱ-ㅎa-z])\s+(\S+동)(?=\s|$)")

USAGE_KEYWORDS = [
    "오피스텔",
    "근린\\s*생활\\s*시설",
    "도시형\\s*생활\\s*주택",
    "공동주택\\s*\\(아파트\\)",
    "업무\\s*시설",
    "숙박\\s*시설",
    "공장",
    "아파트",
]
USAGE_ALT = "|".join(USAGE_KEYWORDS)
DONG_HO = r"(?:\S*?동\s+)?(?:\S*?층\s+)?\S*?호"

ROW_RE = re.compile(
    r"^(?P<code>[ㄱ-ㅎa-z])\s+(?P<dong>\S+동)\s+"
    r"(?P<jibun>[\d][\d,\-]*)\s+"
    r"(?P<name>.+?)\s+"
    rf"(?P<dong_ho>{DONG_HO})\s+"
    rf"(?P<usage>{USAGE_ALT})\s+"
    r"(?P<area>[\d,]+\.?\d*)\s+"
    r"(?P<date1>\d{4}\.\d{2}\.\d{2})\s+"
    r"(?:(?P<purpose>시가참고|담보)\s*)?"
    r"(?P<amount>[\d,]{6,})\s+"
    r"(?P<unit_price>[\d,]{4,})\s+"
    r"(?P<location>\S+)\s+"
    r"(?P<date2>\d{4}\.\d{2}\.\d{2})"
)


@dataclass
class AppraisalCaseRow:
    case_type: str
    code: str
    sido: str | None
    sigungu: str | None
    dong: str
    jibun: str | None
    complex_name: str
    dong_ho: str | None
    usage: str
    exclusive_area: float
    event_date: str
    purpose: str | None
    amount: int  # 만원
    unit_price: int  # 만원/㎡
    location_note: str | None
    approval_date: str | None


class AppraisalParsingError(Exception):
    pass


def _detect_sido_sigungu(text: str) -> tuple[str | None, str | None]:
    match = SIDO_SIGUNGU_RE.search(text)
    if not match:
        return None, None
    sigungu = re.sub(r"\s+", " ", match.group(2)).strip()
    return match.group(1), sigungu


def _clean_row_text(row_lines: list[str]) -> str:
    joined = " ".join(row_lines).replace("\x00", " ")
    joined = re.sub(r"\s+", " ", joined).strip()
    joined = re.sub(r"\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\s*$", "", joined)
    joined = re.sub(r"\s*\[출처[^\]]*\]\s*$", "", joined)
    return joined


def _to_won_as_manwon(value: str) -> int:
    return round(int(value.replace(",", "")) / 10000)


def _parse_date(value: str) -> str:
    year, month, day = value.split(".")
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _parse_section(section_text: str, case_type: str, sido: str | None, sigungu: str | None) -> list[AppraisalCaseRow]:
    starts = list(ROW_START_RE.finditer(section_text))
    rows: list[AppraisalCaseRow] = []

    for i, start in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(section_text)
        row_lines = [ln.strip() for ln in section_text[start.start():end].splitlines() if ln.strip()]
        joined = _clean_row_text(row_lines)

        m = ROW_RE.match(joined)
        if not m:
            continue
        g = m.groupdict()

        rows.append(
            AppraisalCaseRow(
                case_type=case_type,
                code=g["code"],
                sido=sido,
                sigungu=sigungu,
                dong=g["dong"],
                jibun=g["jibun"],
                complex_name=g["name"],
                dong_ho=g["dong_ho"],
                usage=re.sub(r"\s+", "", g["usage"]),
                exclusive_area=float(g["area"].replace(",", "")),
                event_date=_parse_date(g["date1"]),
                purpose=g["purpose"],
                amount=_to_won_as_manwon(g["amount"]),
                unit_price=_to_won_as_manwon(g["unit_price"]),
                location_note=g["location"] if g["location"] != "-" else None,
                approval_date=_parse_date(g["date2"]),
            )
        )

    return rows


def parse_appraisal_pdf(path) -> list[AppraisalCaseRow]:
    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        raise AppraisalParsingError(f"PDF를 읽을 수 없습니다: {e}") from e

    full_text = "\n".join(pages_text).replace("\x00", " ")
    if len(full_text.strip()) < 100:
        raise AppraisalParsingError("텍스트를 추출하지 못했습니다 (스캔본 PDF로 추정, 현재 미지원).")

    sido, sigungu = _detect_sido_sigungu(full_text[:5000])

    headings = list(SECTION_HEADING_RE.finditer(full_text))
    rows: list[AppraisalCaseRow] = []
    for i, heading in enumerate(headings):
        case_type = heading.group(1)
        section_end = headings[i + 1].start() if i + 1 < len(headings) else len(full_text)
        section_text = full_text[heading.end():section_end]
        rows.extend(_parse_section(section_text, case_type, sido, sigungu))

    return rows
