"""네이버 뉴스 검색 API 클라이언트 (openapi.naver.com, 공식 개발자 API).

문서: https://developers.naver.com/docs/serviceapi/search/news/news.md
developers.naver.com에서 애플리케이션을 등록해 NAVER_CLIENT_ID/NAVER_CLIENT_SECRET을 발급받아야 한다.
"""

import requests

from app.core.config import settings

BASE_URL = "https://openapi.naver.com/v1/search/news.json"


class NaverNewsApiError(Exception):
    pass


def fetch_news_items(query: str, display: int = 100, start: int = 1, sort: str = "date") -> list[dict]:
    """query로 뉴스를 검색해 원본 응답 item 목록을 반환한다.

    display: 1~100 (한 번에 가져올 검색 결과 수)
    sort: "date"(최신순) | "sim"(정확도순)
    """

    if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
        raise NaverNewsApiError(
            "NAVER_CLIENT_ID/NAVER_CLIENT_SECRET이 설정되어 있지 않습니다. "
            "developers.naver.com에서 애플리케이션을 등록한 뒤 backend/.env에 추가해주세요."
        )

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": start, "sort": sort}

    try:
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
    except requests.RequestException as e:
        raise NaverNewsApiError(f"네이버 뉴스 API 호출 실패: {e}") from e

    if response.status_code != 200:
        raise NaverNewsApiError(f"네이버 뉴스 API 오류 [{response.status_code}]: {response.text[:300]}")

    try:
        data = response.json()
    except ValueError as e:
        raise NaverNewsApiError(f"네이버 뉴스 API 응답 파싱 실패: {e}") from e

    return data.get("items", [])
