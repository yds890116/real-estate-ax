from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import resolve_property
from app.db.session import get_db
from app.models.registry_analysis import RegistryAnalysis
from app.schemas.registry import RegistryAnalysisResult
from app.schemas.risk import RiskScoreRequest, RiskScoreResult
from app.services.registry_parser import compute_mortgage_total
from app.services.risk_engine import risk_engine
from app.services.valuation_engine import valuation_engine

router = APIRouter()


@router.post("/score", response_model=RiskScoreResult)
def score_risk(payload: RiskScoreRequest, db: Session = Depends(get_db)):
    prop = resolve_property(db, payload.property_id, payload.property)
    valuation = payload.valuation or valuation_engine.estimate(prop, db)

    mortgage_total = None
    if payload.property_id is not None:
        latest_registry = (
            db.query(RegistryAnalysis)
            .filter(RegistryAnalysis.property_id == payload.property_id)
            .order_by(RegistryAnalysis.created_at.desc())
            .first()
        )
        if latest_registry is not None:
            rights = RegistryAnalysisResult.model_validate(latest_registry).rights
            mortgage_total = compute_mortgage_total(rights) or None

    return risk_engine.score(prop, valuation, db, mortgage_total)
