"""Playwright 헤드리스 브라우저로 호갱노노(hogangnono.com) 단지 시세를 수집한다.

동작 확인 경과 (중요, 반드시 읽고 사용할 것):
호갱노노의 핵심 데이터 API `GET /api/apt/bounding`(지도 bbox 내 단지별 실거래가/포털시세를
평형 단위로 내려줌)는 raw HTTP(requests)로는 아무리 쿠키·헤더를 흉내내도 400을 반환한다.
Playwright로 실제 페이지를 열고 Network 탭을 가로채 확인해보니, 이 API는 `x-hogangnono-at`
같은 커스텀 인증 헤더를 요구하는데 이 값은 페이지 자신의 JS(axios 인스턴스)가 내부적으로만
채워 넣는 값이라 `page.evaluate(fetch(...))`로 직접 호출해도(같은 JS 실행 컨텍스트인데도)
헤더가 안 붙어 400이 난다 — 즉 실제 UI 조작(지도 이동 등)으로 발생하는 "진짜" 요청만 통과한다.

또 하나 확인된 것: 사이트 진입 시 Google Ads 광고 슬롯(`web_gateway_pop`, 매번 다른 배너)이
전체 화면을 가리는 iframe으로 뜨고, 자체 앱 설치 유도 모달도 별도로 뜬다. 전자는
googlesyndication.com/doubleclick.net/googleadservices.com/adtrafficquality.google 요청을
차단하면 아예 로드되지 않는다(주의: naver.com 계열 도메인은 지도 렌더링에 필요하므로 절대
차단하면 안 된다 - 차단해보니 "naver 지도 로딩에 실패했습니다" 에러로 전체가 깨졌다). 후자는
`a[data-ga-event="intro,closeBtn"]` 셀렉터로 확실히 닫힌다.

검색창 UI(자동완성 목록 클릭)로 원하는 단지까지 내비게이션하는 것은 광고 타이밍이 매번 달라
신뢰성이 낮았다. 대신 좌표 기반 지도 이동(줌아웃 → 드래그 → 줌인)이 안정적이었는데, "줌 1단계
= 정확히 2배 축척"이라는 이론적 가정(Web Mercator 공식)으로 드래그 픽셀을 계산했더니 매번
오차가 누적돼 목표 지점에 수렴하지 못했다 — 실제 줌 컨트롤의 단계당 축척비가 이론값과 다른
것으로 보인다. 그래서 이론식 대신, 줌아웃 직후 실제로 내려온 bbox(startX/endX/startY/endY)의
폭을 뷰포트 픽셀 폭으로 나눠 "그 순간의 실제 도(degree)/픽셀 비율"을 직접 측정해 드래그 거리를
계산한다 — 어떤 줌 배율 가정도 필요 없는 방식이라 훨씬 정확하다.
"""

import logging
import random
import time

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 순수 광고 도메인만 차단한다 - naver.com 계열(지도 렌더링에 필요)은 절대 포함하지 않는다.
AD_BLOCK_DOMAINS = [
    "googlesyndication.com",
    "doubleclick.net",
    "googleadservices.com",
    "adtrafficquality.google",
    "criteo.com",
]

CLOSE_BTN_SELECTOR = 'a[data-ga-event="intro,closeBtn"]'
VIEWPORT = {"width": 1400, "height": 1000}

# 기본 노출 지역의 중심 좌표(위도, 경도) - 페이지 최초 진입 시 항상 이 위치로 뜬다(라이브 확인됨).
DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG = 37.523003, 127.0547915

ZOOM_OUT_STEPS = 7  # 드래그를 위한 임시 줌아웃 단계 수 (먼 거리도 한 번에 이동할 수 있도록 넉넉히)
ZOOM_IN_BTN = (1360, 798)
ZOOM_OUT_BTN = (1360, 845)
MAP_CENTER_PX = (700, 500)
MAX_CORRECTION_ROUNDS = 5
MATCH_TOLERANCE_DEG = 0.003  # 약 250~300m 이내면 목표가 bbox 안에 든 것으로 본다

MIN_DELAY_SEC = 2.0
MAX_DELAY_SEC = 3.0


class HogangnonoBlockedError(Exception):
    """진짜 실패(구조 변경, 네트워크 오류 등)를 의미 - 절대 가짜 데이터를 만들지 않는다."""


LISTING_SUMMARIES_FETCH_LIMIT = 100


def _politely_wait() -> None:
    time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))


def _normalize_name(name: str) -> str:
    return name.replace(" ", "").strip()


def _match_complex_items(items: list[dict], target_name: str) -> list[dict]:
    """target_name과 이름이 일치하는 단지의 모든 평형(area) 행을 반환한다."""

    target = _normalize_name(target_name)

    exact = [it for it in items if _normalize_name(it.get("name") or "") == target]
    if exact:
        matched_name = exact[0].get("name")
        return [it for it in items if it.get("name") == matched_name]

    partial = [
        it for it in items if target in _normalize_name(it.get("name") or "") or _normalize_name(it.get("name") or "") in target
    ]
    if partial:
        matched_name = partial[0].get("name")
        return [it for it in items if it.get("name") == matched_name]

    return []


def _fetch_listings(page: Page, apt_hash: str) -> list[dict]:
    """단지 상세페이지의 '이 단지 매물 N개 보기'가 호출하는 것과 동일한 매물 목록 API.

    page.evaluate로 이미 로드된 페이지 컨텍스트 안에서 fetch하므로 쿠키/세션이 자동으로
    포함된다. 실패해도 가격 데이터 자체는 유효하므로 예외를 삼키고 빈 리스트를 반환한다.
    """
    try:
        result = page.evaluate(
            """async (args) => {
                const { aptHash, limit } = args;
                const res = await fetch(
                    `/api/v2/item-catalogs/summaries?aptHash=${aptHash}&isAptDetail=false&offset=0&limit=${limit}`,
                    { headers: { accept: 'application/json' } },
                );
                return { status: res.status, body: await res.json() };
            }""",
            {"aptHash": apt_hash, "limit": LISTING_SUMMARIES_FETCH_LIMIT},
        )
    except Exception:
        logger.exception("호갱노노 매물 목록 조회 중 예외 발생")
        return []

    if result.get("status") != 200:
        return []
    return result.get("body", {}).get("data", {}).get("itemCatalogSummaries", [])


def _block_ads(route):
    if any(d in route.request.url for d in AD_BLOCK_DOMAINS):
        route.abort()
    else:
        route.continue_()


def _dismiss_modal(page: Page) -> None:
    try:
        btn = page.locator(CLOSE_BTN_SELECTOR).first
        if btn.count() > 0 and btn.is_visible():
            btn.click(timeout=2000)
            page.wait_for_timeout(300)
    except Exception:
        pass


def _bbox_center(bbox: dict) -> tuple[float, float]:
    return (bbox["startY"] + bbox["endY"]) / 2, (bbox["startX"] + bbox["endX"]) / 2


def _bbox_contains(bbox: dict, lat: float, lng: float, tolerance: float) -> bool:
    return (
        bbox["startX"] - tolerance <= lng <= bbox["endX"] + tolerance
        and bbox["startY"] - tolerance <= lat <= bbox["endY"] + tolerance
    )


def fetch_complex_data(target_name: str, target_lat: float, target_lng: float) -> dict:
    """target_lat/lng(카카오 API로 얻은 좌표) 인근으로 지도를 이동시켜 단지별 실거래가/포털시세와,
    이름이 일치하는 단지의 개별 매물 목록을 함께 가져온다.

    반환값: {"matched_items": list[dict] (평형별 실거래가/포털시세, target_name과 일치하는 단지만),
             "listings": list[dict] (개별 매물 원본, /api/v2/item-catalogs/summaries 결과)}
    일치하는 단지를 찾지 못하면 matched_items/listings 모두 빈 리스트다. 지도 이동이 끝내
    목표 좌표 근처에 도달하지 못하면 HogangnonoBlockedError를 던진다(가짜 데이터를 반환하지 않는다).
    """

    last_bbox: dict | None = None
    last_body: dict | None = None

    def on_response(res):
        nonlocal last_bbox, last_body
        if "apt/bounding" in res.url:
            try:
                body = res.json()
            except Exception:
                return
            qs = dict(pair.split("=") for pair in res.url.split("?", 1)[1].split("&") if "=" in pair)
            try:
                last_bbox = {k: float(qs[k]) for k in ("startX", "endX", "startY", "endY")}
            except (KeyError, ValueError):
                return
            last_body = body

    def wait_for_fresh_bbox(page: Page, timeout_ms: int = 4000) -> None:
        before = last_bbox
        elapsed = 0
        step = 200
        while elapsed < timeout_ms:
            page.wait_for_timeout(step)
            elapsed += step
            if last_bbox is not None and last_bbox != before:
                return

    def drag_toward(page: Page, cur_lat: float, cur_lng: float, dst_lat: float, dst_lng: float) -> None:
        for _ in range(ZOOM_OUT_STEPS):
            _dismiss_modal(page)
            page.mouse.click(*ZOOM_OUT_BTN)
            page.wait_for_timeout(350)
        wait_for_fresh_bbox(page)
        _dismiss_modal(page)

        if last_bbox is None:
            raise HogangnonoBlockedError("줌아웃 후 지도 데이터 응답을 확인하지 못했습니다.")

        # 그 순간 실제로 내려온 bbox 폭으로 도(degree)/픽셀 비율을 직접 측정한다 (이론적 줌 공식 대신).
        deg_per_px_x = (last_bbox["endX"] - last_bbox["startX"]) / VIEWPORT["width"]
        deg_per_px_y = (last_bbox["endY"] - last_bbox["startY"]) / VIEWPORT["height"]

        dlng = dst_lng - cur_lng
        dlat = dst_lat - cur_lat
        drag_dx_px = dlng / deg_per_px_x if deg_per_px_x else 0
        drag_dy_px = -(dlat / deg_per_px_y) if deg_per_px_y else 0  # 위도가 커질수록(북쪽) 화면 위로 이동해야 함

        start_x, start_y = MAP_CENTER_PX
        end_x = max(50, min(VIEWPORT["width"] - 50, start_x - drag_dx_px))
        end_y = max(50, min(VIEWPORT["height"] - 50, start_y - drag_dy_px))
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(end_x, end_y, steps=25)
        page.mouse.up()
        wait_for_fresh_bbox(page)
        _dismiss_modal(page)

        for _ in range(ZOOM_OUT_STEPS):
            _dismiss_modal(page)
            page.mouse.click(*ZOOM_IN_BTN)
            page.wait_for_timeout(350)
        wait_for_fresh_bbox(page)
        _dismiss_modal(page)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=USER_AGENT, viewport=VIEWPORT)
            page = context.new_page()
            page.route("**/*", _block_ads)
            page.on("response", on_response)

            _politely_wait()
            page.goto("https://hogangnono.com/", timeout=30000)
            page.wait_for_timeout(3500)
            _dismiss_modal(page)
            page.wait_for_timeout(400)

            cur_lat, cur_lng = DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
            reached = False
            for _ in range(MAX_CORRECTION_ROUNDS):
                drag_toward(page, cur_lat, cur_lng, target_lat, target_lng)

                if last_bbox is None:
                    raise HogangnonoBlockedError("지도 이동 후 단지 데이터 응답을 확인하지 못했습니다.")

                if _bbox_contains(last_bbox, target_lat, target_lng, MATCH_TOLERANCE_DEG):
                    reached = True
                    break

                cur_lat, cur_lng = _bbox_center(last_bbox)

            if not reached:
                raise HogangnonoBlockedError(
                    f"{MAX_CORRECTION_ROUNDS}회 보정에도 목표 좌표 근처로 지도를 이동시키지 못했습니다."
                )

            if last_body is None:
                raise HogangnonoBlockedError("단지 데이터 응답이 없습니다.")

            items = last_body.get("data", [])
            matched = _match_complex_items(items, target_name)

            listings: list[dict] = []
            if matched:
                apt_hash = matched[0].get("id")
                if apt_hash:
                    listings = _fetch_listings(page, apt_hash)

            return {"matched_items": matched, "listings": listings}
        except HogangnonoBlockedError:
            raise
        except Exception as e:  # noqa: BLE001 - naver_scraper.py와 동일하게 폭넓게 잡아 차단으로 보고
            logger.exception("호갱노노 수집 중 예외 발생")
            raise HogangnonoBlockedError(f"수집 중 오류: {e}") from e
        finally:
            browser.close()
