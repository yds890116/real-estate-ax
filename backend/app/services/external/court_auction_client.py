"""Playwright 헤드리스 브라우저로 대한민국 법원 법원경매정보(courtauction.go.kr) 물건상세검색 결과를 수집한다.

동작 확인 경과 (중요, 반드시 읽고 사용할 것):
이 사이트의 핵심 검색 API `POST /pgj/pgjsearch/searchControllerMain.on`은 raw HTTP는 물론
Playwright의 `page.evaluate(fetch(...))`(같은 브라우저 세션 쿠키를 쓰는 in-page fetch)로도 호출이
안 된다 - `submissionid`/`sc-userid` 커스텀 헤더를 그대로 흉내내도 400이 난다. WebSquare
프레임워크가 폼 제출 시 자기 내부 상태(위젯 모델)를 기준으로 요청을 조립하기 때문으로 보이며,
실제 검색 버튼 클릭(진짜 UI 이벤트)으로 발생한 요청만 통과한다 - hogangnono_client.py의
`/api/apt/bounding`과 동일한 패턴. 그래서 이 클라이언트는 실제 폼 요소를 채우고 버튼을 클릭해
`page.on("response")`로 결과를 가로채는 방식으로만 동작한다.

또한 법원/소재지를 "전체"로 두고 검색하면 매번 "법원/소재지를 전체로 선택할 경우...
용도 조건의 중분류를 반드시 선택하시기 바랍니다"라는 알림이 뜨고, 중분류를 실제로 선택하지
않으면 몇 번을 눌러도 검색이 진행되지 않는다(단순 안내가 아니라 사실상의 필수 조건). 그래서
용도 대분류=건물(중분류 4종: 주거용건물/상업업무용건물/산업및기타시설/대지관련용도) +
대분류=토지(중분류 없음, 대분류만으로 검색 가능)를 순회하며 전국 단위로 수집한다.

페이지네이션: 서버가 페이지당 10건으로 고정되어 있고(dma_pageInfo.pageSize를 UI 밖에서 바꿀
방법을 찾지 못함), 카테고리당 결과가 많으면(전국 2주 매각기일 기준 최대 1만 건대) 끝까지
수집하는 건 비현실적이라 카테고리당 최대 `MAX_PAGES_PER_CATEGORY` 페이지까지만 수집한다.
"오늘 날짜 기준" 요구사항에 맞춰 매각기일 검색 기간을 오늘 하루로 좁혀서 카테고리당 결과 수
자체를 줄인다.

이용약관 관련 메모: 법원경매정보 이용약관 제15조는 '갑'(법원행정처)의 동의 없이 서비스 내용을
가공하거나 입찰참가 외 영리목적으로 이용하는 행위를 금지하되, 이 조항이 적용되는 '이용자(을)'를
회원등록을 한 자로 명시적으로 정의하고 있다. 사용자와 상의한 결과 "로그인/회원가입도 가능하니
필요 시 진행" 방침을 확인했다 - 현재 버전은 비회원 상태로 공개된 물건상세검색 결과만 조회한다
(회원 전용 기능은 사용하지 않음).
"""

import logging
from datetime import date

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
VIEWPORT = {"width": 1400, "height": 1000}

SEARCH_PAGE_URL = "https://www.courtauction.go.kr/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F00.xml"

LCL_SELECT_ID = "#mf_wfm_mainFrame_sbx_rletLclLst"
MCL_SELECT_ID = "#mf_wfm_mainFrame_sbx_rletMclLst"
DATE_START_ID = "#mf_wfm_mainFrame_cal_rletPerdStr_input"
DATE_END_ID = "#mf_wfm_mainFrame_cal_rletPerdEnd_input"

# (대분류, 중분류) - 중분류가 None이면 별도 선택 없이(=대분류만으로 충분한 경우) 진행한다.
CATEGORIES: list[tuple[str, str | None]] = [
    ("건물", "주거용건물"),
    ("건물", "상업업무용건물"),
    ("건물", "산업및기타시설"),
    ("건물", "대지관련용도"),
    ("토지", None),
]

MAX_PAGES_PER_CATEGORY = 5
PAGE_SIZE = 10  # 서버 고정값


class CourtAuctionBlockedError(Exception):
    """진짜 실패(구조 변경, 네트워크 오류, WAF 차단 등)를 의미 - 절대 가짜 데이터를 만들지 않는다."""


def _dismiss_notice_popups(page: Page) -> None:
    """홈페이지 진입 시 뜨는 공지사항 팝업들을 최대 5회까지 닫는다. 검색 페이지 직행 시에는 보통 뜨지 않는다."""
    for _ in range(5):
        try:
            btns = page.locator("text=닫기")
            n = btns.count()
            if n == 0:
                return
            btns.first.click(timeout=1500)
            page.wait_for_timeout(400)
        except Exception:
            return


def _select_category(page: Page, lcl: str, mcl: str | None) -> None:
    page.select_option(LCL_SELECT_ID, label=lcl, timeout=5000)
    page.wait_for_timeout(1000)
    if mcl:
        page.select_option(MCL_SELECT_ID, label=mcl, timeout=5000)
        page.wait_for_timeout(600)


def _set_date_range(page: Page, target: date) -> None:
    ymd_dot = target.strftime("%Y.%m.%d")
    page.fill(DATE_START_ID, ymd_dot)
    page.fill(DATE_END_ID, ymd_dot)
    page.keyboard.press("Tab")
    page.wait_for_timeout(400)


def _submit_search(page: Page) -> None:
    page.get_by_role("button", name="검색", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(1200)
    # 법원/소재지=전체 + 용도 중분류 미선택 조합일 때만 뜨는 안내창 - 방어적으로 처리
    confirm_btn = page.get_by_role("button", name="확인").first
    if confirm_btn.count() > 0:
        confirm_btn.click(timeout=3000)
        page.wait_for_timeout(800)


def fetch_new_listings(target_date: date, max_pages_per_category: int = MAX_PAGES_PER_CATEGORY) -> list[dict]:
    """target_date(매각기일 기준)에 해당하는 전국 부동산 경매 물건을 카테고리별로 수집한다.

    반환값은 /pgj/pgjsearch/searchControllerMain.on 원본 행(dlt_srchResult 각 원소)의 리스트다.
    이미 알려진 오류(사이트 구조 변경, 응답 없음 등)는 CourtAuctionBlockedError로 감싸 던진다.
    개별 카테고리 조회 실패는 조용히 건너뛰고 나머지 카테고리는 계속 수집한다.
    """

    rows: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=USER_AGENT, viewport=VIEWPORT)
            page = context.new_page()

            any_category_succeeded = False

            for lcl, mcl in CATEGORIES:
                captured: list[dict] = []

                def on_response(res, _sink=captured):
                    if "searchControllerMain" in res.url:
                        try:
                            _sink.append(res.json())
                        except Exception:
                            pass

                page.on("response", on_response)
                try:
                    page.goto(SEARCH_PAGE_URL, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)
                    _dismiss_notice_popups(page)

                    _select_category(page, lcl, mcl)
                    _set_date_range(page, target_date)
                    _submit_search(page)
                    page.wait_for_timeout(1500)

                    for page_no in range(2, max_pages_per_category + 1):
                        pager = page.locator(f"#mf_wfm_mainFrame_pgl_gdsDtlSrchPage_page_{page_no}")
                        if pager.count() == 0:
                            break
                        pager.first.click(timeout=3000)
                        page.wait_for_timeout(1200)

                    for body in captured:
                        data = body.get("data") if isinstance(body, dict) else None
                        if not isinstance(data, dict):
                            continue
                        page_rows = data.get("dlt_srchResult") or []
                        rows.extend(page_rows)

                    if captured:
                        any_category_succeeded = True
                except Exception:
                    logger.exception("법원경매정보 카테고리(%s/%s) 수집 중 예외 발생", lcl, mcl)
                finally:
                    page.remove_listener("response", on_response)

            if not any_category_succeeded:
                raise CourtAuctionBlockedError("모든 카테고리에서 검색 결과를 가져오지 못했습니다.")

            return rows
        except CourtAuctionBlockedError:
            raise
        except Exception as e:  # noqa: BLE001 - 다른 클라이언트들과 동일하게 폭넓게 잡아 차단으로 보고
            logger.exception("법원경매정보 수집 중 예외 발생")
            raise CourtAuctionBlockedError(f"수집 중 오류: {e}") from e
        finally:
            browser.close()
