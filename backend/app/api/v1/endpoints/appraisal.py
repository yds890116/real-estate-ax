from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.appraisal_case import AppraisalCase
from app.schemas.appraisal import (
    AppraisalCaseResponse,
    AppraisalIngestResult,
    AppraisalSearchRequest,
    AppraisalSearchResult,
)
from app.schemas.property import PropertyBase
from app.services.appraisal_ingest import ingest_appraisal_samples
from app.services.appraisal_search import search_similar_cases

router = APIRouter()


@router.post("/ingest", response_model=AppraisalIngestResult)
def ingest_appraisal(db: Session = Depends(get_db)):
    """설정된 샘플 폴더(감정평가서 PDF)를 파싱해 appraisal_cases에 적재한다."""

    result = ingest_appraisal_samples(db)
    return AppraisalIngestResult(**result)


@router.get("/cases", response_model=list[AppraisalCaseResponse])
def list_appraisal_cases(
    sigungu: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(AppraisalCase)
    if sigungu:
        query = query.filter(AppraisalCase.sigungu == sigungu)
    return query.order_by(AppraisalCase.id).limit(limit).all()


@router.post("/search", response_model=AppraisalSearchResult)
def search_appraisal(payload: AppraisalSearchRequest, db: Session = Depends(get_db)):
    prop = PropertyBase(
        address=f"{payload.sido} {payload.sigungu} {payload.dong or ''}".strip(),
        sido=payload.sido,
        sigungu=payload.sigungu,
        dong=payload.dong,
        property_type=payload.usage,
        exclusive_area=payload.exclusive_area,
    )
    return search_similar_cases(db, prop, usage=payload.usage, top_k=payload.top_k)
