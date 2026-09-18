"""한국부동산원 부동산테크(rtech.or.kr) 내부 API 클라이언트.

Playwright로 https://rtech.or.kr/land/landMap.do 접속 후 Network 탭(XHR/fetch)을 가로채
실제 호출되는 내부 API를 직접 확인해 구현했다 (공식 문서 없음 - 화면이 호출하는 그대로).

확인 방법: 브라우저 세션/쿠키 없이 순수 requests.post()만으로도 200(201) 응답이 정상적으로
오는 것을 라이브로 검증했다 — CSRF 토큰이나 로그인 세션이 전혀 필요 없다. 다만 예의상
Referer/X-Requested-With 헤더는 유지한다.

확인된 요청/응답 흐름 (시도 → 구/군 → 동 → 단지목록 → 단지별 상세):
1) POST /Addr/getDoList.do                              → 시도 목록
2) POST /Addr/getGuList.do        {doCode}               → 구/군 목록
3) POST /Addr/getDongList.do      {doCode, cityCode}      → 동 목록 (10자리 법정동코드)
4) POST /Addr/getAptList.do       {reg_code, eub_code}    → 단지 목록(SEQ, 세대수, 좌표)
   reg_code = 법정동코드 앞 5자리(시군구), eub_code = 그 다음 3자리(읍면동, 뒤 두자리 00 제외)
5) POST /maktPrc/getMarketPriceAptInfo.do       {aptSeq}                    → 단지 기본정보
6) POST /maktPrc/marketPriceBaseDateList.do     {categoryCd, year}          → 시세 발표 기준일 목록
7) POST /maktPrc/getMarketPriceAptAreaList.do   {aptSeq, fnDateToOpenDt}    → 평형별 매매/전세 시세
8) POST /maktPrc/getMarketPriceAptPyongTypeList.do {aptSeq}                 → 평형 목록(PYONG_SEQ 등)
9) POST /maktPrc/getRealPriceMonthlyList.do  {categoryCd,mode,year,aptSeq,dealYm,pyong} → 실거래가 내역

fnDateToOpenDt는 marketPriceBaseDateList.do 응답의 가장 최근 AMT_DT를 사용한다(라이브 확인).
"""

import time

import requests

BASE_URL = "https://rtech.or.kr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://rtech.or.kr/land/landMap.do",
}

MIN_DELAY_SEC = 2.0
MAX_DELAY_SEC = 3.0


class RtechApiError(Exception):
    pass


def _politely_wait() -> None:
    """요청 사이 2~3초 지연 - 과도한 요청 방지."""
    import random

    time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))


def _post(path: str, data: dict | None = None) -> list | dict:
    _politely_wait()
    try:
        response = requests.post(f"{BASE_URL}{path}", data=data, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RtechApiError(f"부동산테크 API 호출 실패 ({path}): {e}") from e

    try:
        return response.json()
    except ValueError as e:
        raise RtechApiError(f"부동산테크 API 응답 파싱 실패 ({path}): {e}") from e


def fetch_do_list() -> list[dict]:
    """시도 목록. [{"DO_CODE":"11","DO_NAME":"서울특별시"}, ...]"""
    return _post("/Addr/getDoList.do")


def fetch_gu_list(do_code: str) -> list[dict]:
    """구/군 목록. [{"CITY_CODE":"680","CITY_NAME":"강남구"}, ...]"""
    return _post("/Addr/getGuList.do", {"doCode": do_code})


def fetch_dong_list(do_code: str, city_code: str) -> list[dict]:
    """동 목록. [{"DONG_NAME":"가회동","DONG_CODE":"1111014600"}, ...] (10자리 법정동코드)"""
    return _post("/Addr/getDongList.do", {"doCode": do_code, "cityCode": city_code})


def fetch_apt_list(reg_code: str, eub_code: str) -> list[dict]:
    """단지 목록. [{"APT_NAME":..,"SEQ":24047,"X":..,"Y":..,"ADDRCD":..,"KTECH_H_NUM":"529","KTECH_TOT_DONG":1}]"""
    return _post("/Addr/getAptList.do", {"reg_code": reg_code, "eub_code": eub_code})


def fetch_apt_info(apt_seq: int) -> dict:
    """단지 기본정보(단지명/세대수/면적/주소 등)."""
    return _post("/maktPrc/getMarketPriceAptInfo.do", {"aptSeq": apt_seq})


def fetch_market_price_base_date_list(category_cd: int = 1, year: int | None = None) -> list[dict]:
    """시세 발표 기준일 목록. [{"OPEN_DT":"2026-09-18","AMT_DT":"2026-09-14"}, ...] (최신순)"""
    from datetime import date

    return _post("/maktPrc/marketPriceBaseDateList.do", {"categoryCd": category_cd, "year": year or date.today().year})


def fetch_apt_area_price_list(apt_seq: int, fn_date_to_open_dt: str) -> list[dict]:
    """평형별 매매/전세 시세 목록 (S_LOWER/UPPER_PRICE=매매, R_LOWER/UPPER_PRICE=전세, 단위 만원)."""
    return _post("/maktPrc/getMarketPriceAptAreaList.do", {"aptSeq": apt_seq, "fnDateToOpenDt": fn_date_to_open_dt})


def fetch_apt_pyong_type_list(apt_seq: int) -> list[dict]:
    """평형 목록. [{"PYONG":10,"PRIV_AREA":28.1,"PYONG_SEQ":647548}, ...]"""
    return _post("/maktPrc/getMarketPriceAptPyongTypeList.do", {"aptSeq": apt_seq})


def fetch_real_price_monthly_list(apt_seq: int, pyong: float, deal_ym: str, category_cd: int = 1, mode: str = "ALL", year: int = 1) -> list[dict]:
    """실거래가 내역. TRADE_MODE(관측값: "RENT"=전세/월세 계열), M_DEAL_AMT(만원), M_DEAL_YMD 등."""
    return _post(
        "/maktPrc/getRealPriceMonthlyList.do",
        {"categoryCd": category_cd, "mode": mode, "year": year, "aptSeq": apt_seq, "dealYm": deal_ym, "pyong": pyong},
    )
