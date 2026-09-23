from fastapi import APIRouter, HTTPException

from app.schemas.search import AutocompleteSuggestionResponse
from app.services.external.kakao_client import KakaoApiError, search_autocomplete

router = APIRouter()


@router.get("/autocomplete", response_model=list[AutocompleteSuggestionResponse])
def autocomplete(query: str, size: int = 5):
    """주소/단지명 입력 자동완성 (카카오맵 주소·키워드 검색 결과 결합)."""

    if len(query.strip()) < 2:
        return []
    try:
        suggestions = search_autocomplete(query, size=size)
    except KakaoApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return [AutocompleteSuggestionResponse(**s.__dict__) for s in suggestions]
