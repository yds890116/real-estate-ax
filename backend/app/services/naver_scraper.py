"""Playwright 헤드리스 브라우저로 네이버 부동산(fin.land.naver.com) 매물을 수집한다.

동작 확인 경과 (중요, 반드시 읽고 사용할 것):
raw HTTP(requests)로는 검색 엔드포인트가 fin.land.naver.com으로 리다이렉트된 후 무응답으로
타임아웃되거나, 구 API(m.land.naver.com/cluster/ajax/articleList)는 200 응답에 항상 빈 값만
내려왔다. 실제 Playwright(진짜 Chromium)로 재현하자 원인이 드러났는데, fin.land.naver.com의
프론트엔드 API(front-api/v1/...)가 **첫 요청부터 HTTP 429 TOO_MANY_REQUESTS**
({"detailCode":"TOO_MANY_REQUESTS"})를 반환했다. 15초 대기 후 재시도해도 동일해 일시적
레이트리밋이 아니라 이 환경의 아웃바운드 IP(클라우드/샌드박스 IP)에 대한 선제적 차단으로
보인다. 즉, 요청 사이 딜레이를 넣어도(요구사항 3, 아래 구현되어 있음) 근본적으로 해결되지
않는 차단이다 — 실제 주거용/사무용 네트워크에서 실행하면 동작할 가능성이 있다.

이런 이유로 매물 카드의 정확한 DOM 구조를 실측하지 못한 채 작성했다. 파싱은 카드 컨테이너
후보 셀렉터를 순서대로 시도한 뒤, 카드 텍스트 전체에서 정규식으로 거래유형/가격/면적/층수/
등록일을 추출하는 방식을 썼다(등기부등본 파서와 동일한 전략). 차단이 풀려 실제 응답을 받게
되면 CARD_SELECTORS와 정규식을 실제 마크업에 맞춰 보정해야 할 수 있다.
"""

import logging
import random
import re
import time
from dataclasses import dataclass, field

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

SEARCH_URL = "https://fin.land.naver.com/search?query={query}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

MIN_DELAY_SEC = 2.0
MAX_DELAY_SEC = 3.0

# 매물 카드로 보이는 요소 후보 (실제 마크업 미확인 상태의 최선 추정 — 위 모듈 docstring 참고)
CARD_SELECTORS = [
    "[class*='ArticleItem']",
    "[class*='article-item']",
    "[class*='listItem']",
    "li[class*='item']",
    "article",
]

TRADE_TYPE_PATTERN = re.compile(r"(매매|전세|월세)")
AREA_PATTERN = re.compile(r"(\d{2,3}(?:\.\d{1,2})?)\s*㎡")
FLOOR_PATTERN = re.compile(r"(\d{1,3})\s*/\s*\d{1,3}\s*층|(\d{1,3})층")
DATE_PATTERN = re.compile(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})")
# "63억 8,000" / "20억 2,500" / "9,700" (억 없이 만원 단위만) / "4억" 등
PRICE_PATTERN = re.compile(r"(\d{1,3})\s*억\s*([\d,]{0,7})|(?<!\d)([\d,]{4,7})(?!\s*㎡)")


class NaverScrapeBlockedError(Exception):
    """네이버가 요청을 차단(429 등)했을 때 발생 — 절대로 가짜 데이터를 생성하지 않고 이 예외를 던진다."""


@dataclass
class ScrapedListing:
    complex_name: str
    exclusive_area: float
    floor: str | None
    trade_type: str
    price: int  # 만원
    monthly_rent: int | None
    realtor: str | None
    listed_date: str | None


@dataclass
class ScrapeResult:
    complex_name: str
    listings: list[ScrapedListing] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None


def _parse_price_to_manwon(text: str) -> int | None:
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    eok_str, remain_str, plain_str = match.groups()
    if eok_str is not None:
        eok = int(eok_str)
        remain = int(remain_str.replace(",", "")) if remain_str else 0
        return eok * 10000 + remain
    if plain_str:
        return int(plain_str.replace(",", ""))
    return None


def _parse_card_text(card_text: str, complex_name: str) -> ScrapedListing | None:
    trade_match = TRADE_TYPE_PATTERN.search(card_text)
    area_match = AREA_PATTERN.search(card_text)
    if not trade_match or not area_match:
        return None

    trade_type = trade_match.group(1)
    exclusive_area = float(area_match.group(1))

    floor_match = FLOOR_PATTERN.search(card_text)
    floor = None
    if floor_match:
        floor_num = floor_match.group(1) or floor_match.group(2)
        floor = f"{floor_num}층"

    date_match = DATE_PATTERN.search(card_text)
    listed_date = None
    if date_match:
        y, m, d = date_match.groups()
        listed_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    price = _parse_price_to_manwon(card_text)
    if price is None:
        return None

    monthly_rent = None
    if trade_type == "월세":
        # "보증금 / 월세" 두 금액이 나열되는 경우가 많아 두 번째 금액을 월세로 잡는다.
        all_amounts = list(PRICE_PATTERN.finditer(card_text))
        if len(all_amounts) >= 2:
            second = _parse_price_to_manwon(card_text[all_amounts[1].start() :])
            if second is not None and second < price:
                monthly_rent = second

    return ScrapedListing(
        complex_name=complex_name,
        exclusive_area=exclusive_area,
        floor=floor,
        trade_type=trade_type,
        price=price,
        monthly_rent=monthly_rent,
        realtor=None,
        listed_date=listed_date,
    )


def _politely_wait() -> None:
    """요청 사이 2~3초 무작위 지연 — 과도한 요청 방지(요구사항 3)."""
    time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))


def _extract_listings(page: Page, complex_name: str) -> list[ScrapedListing]:
    for selector in CARD_SELECTORS:
        cards = page.query_selector_all(selector)
        if len(cards) >= 2:  # 후보 셀렉터가 실제 매물 목록일 가능성이 높은 경우만 채택
            break
    else:
        return []

    listings = []
    for card in cards:
        text = card.inner_text().strip()
        if not text:
            continue
        parsed = _parse_card_text(text, complex_name)
        if parsed is not None:
            listings.append(parsed)
    return listings


def scrape_complex_listings(complex_name: str, max_listings: int = 20) -> ScrapeResult:
    """단지명(또는 단지 코드)으로 네이버 부동산 매물 페이지에 접속해 매물을 수집한다.

    차단(429 등)되면 ScrapeResult.blocked=True와 사유를 반환한다 — 실패를 감추고
    가짜 데이터를 만들어내지 않는다. 호출부에서 이 신호를 보고 샘플 데이터로 폴백할지
    결정한다."""

    result = ScrapeResult(complex_name=complex_name)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 900})
            page = context.new_page()

            blocked_status: list[int] = []
            page.on(
                "response",
                lambda r: blocked_status.append(r.status)
                if "front-api" in r.url and r.status == 429
                else None,
            )

            _politely_wait()
            page.goto(SEARCH_URL.format(query=complex_name), wait_until="networkidle", timeout=20000)

            if blocked_status or "404.html" in page.url:
                result.blocked = True
                result.block_reason = (
                    "네이버 부동산 API가 429(Too Many Requests)를 반환하며 요청을 차단했습니다. "
                    "이 서버의 발신 IP가 선제적으로 제한된 것으로 보이며, 요청 지연으로는 해결되지 않습니다."
                )
                logger.warning("네이버 부동산 스크래핑 차단: %s", result.block_reason)
                return result

            listings = _extract_listings(page, complex_name)
            if not listings:
                result.blocked = True
                result.block_reason = "매물 목록을 찾지 못했습니다 (페이지 구조가 예상과 다르거나 검색 결과가 없음)."
                return result

            result.listings = listings[:max_listings]
            return result
        except Exception as e:  # noqa: BLE001 - 스크래핑은 실패 형태가 다양해 폭넓게 잡고 차단으로 보고한다
            logger.exception("네이버 부동산 스크래핑 중 예외 발생")
            result.blocked = True
            result.block_reason = f"스크래핑 중 오류: {e}"
            return result
        finally:
            browser.close()
