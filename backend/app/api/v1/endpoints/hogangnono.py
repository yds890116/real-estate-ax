from fastapi import APIRouter

from app.schemas.hogangnono import HogangnonoComplexResult
from app.services.hogangnono_service import get_complex_price

router = APIRouter()


@router.get("/price", response_model=HogangnonoComplexResult)
def get_price(query: str, complex_name: str | None = None):
    """호갱노노에서 단지 실거래가·포털시세를 실시간 수집한다.

    Playwright로 실제 지도를 이동시키며 조회하므로 응답까지 10~20초 정도 걸릴 수 있다.
    """

    return get_complex_price(query, complex_name_hint=complex_name)
