from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import resolve_property
from app.db.session import get_db
from app.models.property import Property
from app.models.registry_analysis import RegistryAnalysis
from app.schemas.analysis import PropertyAnalysis
from app.schemas.property import PropertyCreate, PropertyResponse
from app.schemas.opinion import OpinionUpdateRequest, ReviewOpinionResult
from app.schemas.registry import RegistryAnalysisResult
from app.services.appraisal_search import search_similar_cases
from app.services.cost_income_valuation import estimate_cost_income
from app.services.land_valuation_service import get_land_valuation
from app.services.listing_comparison import compare_to_market
from app.services.listing_service import get_cached_or_sample_listings
from app.services.opinion_service import OpinionNotFoundError, generate_opinion, get_opinion, update_opinion
from app.services.registry_parser import compute_mortgage_total
from app.services.risk_engine import risk_engine
from app.services.rone_index_service import get_region_trend_features
from app.services.valuation_engine import valuation_engine

COMPARABLE_SALE_TYPES = {"아파트", "빌라", "연립다세대"}

router = APIRouter()


@router.post("", response_model=PropertyResponse, status_code=201)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db)):
    db_property = Property(**payload.model_dump())
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return db_property


@router.get("", response_model=list[PropertyResponse])
def list_properties(
    sido: str | None = None,
    sigungu: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Property)
    if sido:
        query = query.filter(Property.sido == sido)
    if sigungu:
        query = query.filter(Property.sigungu == sigungu)
    return query.order_by(Property.created_at.desc()).all()


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    db_property = db.get(Property, property_id)
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_property


@router.get("/{property_id}/analysis", response_model=PropertyAnalysis)
def get_property_analysis(property_id: int, db: Session = Depends(get_db)):
    """종합분석 화면(핵심 UX)에서 호출하는 시세+리스크 통합 조회 API."""

    db_property = db.get(Property, property_id)
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")

    prop = resolve_property(db, property_id=property_id, property_payload=None)
    valuation = valuation_engine.estimate(prop, db)

    latest_registry = (
        db.query(RegistryAnalysis)
        .filter(RegistryAnalysis.property_id == property_id)
        .order_by(RegistryAnalysis.created_at.desc())
        .first()
    )
    registry = None
    mortgage_total = None
    if latest_registry is not None:
        registry = RegistryAnalysisResult.model_validate(latest_registry)
        mortgage_total = compute_mortgage_total(registry.rights) or None
        registry.mortgage_total = mortgage_total
        registry.estimated_price = valuation.estimated_price

    land_valuation = get_land_valuation(db, prop)
    risk = risk_engine.score(prop, valuation, db, mortgage_total, land_valuation.land_valuation_score)

    appraisal = search_similar_cases(db, prop, usage=prop.property_type)

    listings = None
    listing_comparison = None
    if prop.complex_name:
        reference_area = appraisal.reference_area or prop.exclusive_area
        listings = get_cached_or_sample_listings(
            db, prop.complex_name, reference_area, appraisal.reference_price_per_area
        )
        listing_comparison = compare_to_market(
            listings.listings,
            reference_area,
            appraisal.reference_price_per_area,
            len(appraisal.cases),
        )

    regional_trend = get_region_trend_features(db, prop.sido, prop.sigungu)
    cost_income_estimate = None if prop.property_type in COMPARABLE_SALE_TYPES else estimate_cost_income(prop)

    return PropertyAnalysis(
        property=PropertyResponse.model_validate(db_property),
        valuation=valuation,
        risk=risk,
        registry=registry,
        appraisal=appraisal,
        listings=listings,
        regional_trend=regional_trend,
        cost_income_estimate=cost_income_estimate,
        listing_comparison=listing_comparison,
        land_valuation=land_valuation,
    )


@router.post("/{property_id}/opinion/generate", response_model=ReviewOpinionResult)
def generate_property_opinion(property_id: int, db: Session = Depends(get_db)):
    """기능1~3(+등기부) 결과를 종합해 심사의견서 초안을 생성한다."""

    if db.get(Property, property_id) is None:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        opinion = generate_opinion(db, property_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return opinion


@router.get("/{property_id}/opinion", response_model=ReviewOpinionResult)
def get_property_opinion(property_id: int, db: Session = Depends(get_db)):
    opinion = get_opinion(db, property_id)
    if opinion is None:
        raise HTTPException(status_code=404, detail="아직 생성된 심사의견이 없습니다.")
    return opinion


@router.put("/{property_id}/opinion", response_model=ReviewOpinionResult)
def update_property_opinion(property_id: int, payload: OpinionUpdateRequest, db: Session = Depends(get_db)):
    """심사역이 수정한 최종본을 저장한다 (이전 버전은 edit_history에 보관)."""

    try:
        return update_opinion(db, property_id, payload.content)
    except OpinionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
