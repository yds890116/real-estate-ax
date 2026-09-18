from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rtech import RtechComparisonResult, RtechDongCollectResult
from app.services.external.rtech_client import RtechApiError, fetch_dong_list, fetch_do_list, fetch_gu_list
from app.services.rtech_collection_service import collect_dong
from app.services.rtech_comparison_service import compare_complex

router = APIRouter()


@router.get("/regions/do")
def list_do():
    """시도 목록 (부동산테크 지역 선택 1단계)."""
    try:
        return fetch_do_list()
    except RtechApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/regions/gu")
def list_gu(do_code: str):
    """구/군 목록 (2단계)."""
    try:
        return fetch_gu_list(do_code)
    except RtechApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/regions/dong")
def list_dong(do_code: str, city_code: str):
    """동 목록 (3단계)."""
    try:
        return fetch_dong_list(do_code, city_code)
    except RtechApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/collect", response_model=RtechDongCollectResult)
def run_collect_dong(do_code: str, city_code: str, dong_code: str, dong_name: str = "", db: Session = Depends(get_db)):
    """동 1곳의 단지 목록·시세·실거래가를 수집한다 (요청 사이 2~3초 지연 자동 적용, 동 하나당 수 분 소요될 수 있음)."""

    return RtechDongCollectResult(**collect_dong(db, do_code, city_code, dong_code, dong_name))


@router.get("/compare", response_model=RtechComparisonResult)
def get_comparison(complex_name: str, sigungu: str | None = None, db: Session = Depends(get_db)):
    """부동산테크 시세·실거래가와 국토교통부 실거래가를 같은 단지·평형 기준으로 나란히 비교한다."""

    result = compare_complex(db, complex_name, sigungu)
    if result is None:
        raise HTTPException(status_code=404, detail=f"부동산테크에서 '{complex_name}' 단지를 찾지 못했습니다. 먼저 /rtech/collect로 해당 지역을 수집해주세요.")
    return RtechComparisonResult(**result)
