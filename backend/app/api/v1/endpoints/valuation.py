from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import resolve_property
from app.db.session import get_db
from app.ml.train import TrainingDataError, train_valuation_model
from app.ml.valuation_model import xgb_valuation_model
from app.schemas.valuation import ValuationModelTrainResult, ValuationRequest, ValuationResult
from app.services.valuation_engine import valuation_engine

router = APIRouter()


@router.post("/estimate", response_model=ValuationResult)
def estimate_valuation(payload: ValuationRequest, db: Session = Depends(get_db)):
    prop = resolve_property(db, payload.property_id, payload.property)
    return valuation_engine.estimate(prop, db)


@router.post("/train", response_model=ValuationModelTrainResult)
def train_model(db: Session = Depends(get_db)):
    """market_transactions에 수집된 실거래가로 XGBoost 시세 추정 모델을 재학습한다."""

    try:
        metrics = train_valuation_model(db)
    except TrainingDataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    xgb_valuation_model.reload()
    return ValuationModelTrainResult(**metrics)
