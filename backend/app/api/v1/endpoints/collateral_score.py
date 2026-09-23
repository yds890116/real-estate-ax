from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.collateral_score_model import collateral_score_model
from app.ml.collateral_score_train import TrainingDataError, train_collateral_score_model
from app.schemas.collateral_score import CollateralScoreModelInfo, CollateralScoreTrainResult
from app.services.batch_collection_service import ensure_onbid_sample_data
from app.services.collateral_scoring_service import get_model_info

router = APIRouter()


@router.post("/train", response_model=CollateralScoreTrainResult)
def train_model(db: Session = Depends(get_db)):
    """온비드 공매 물건 누적 데이터로 담보 스코어링 XGBoost 모델을 학습한다."""

    ensure_onbid_sample_data(db)
    try:
        result = train_collateral_score_model(db)
    except TrainingDataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    collateral_score_model.reload()
    return CollateralScoreTrainResult(**result)


@router.get("/model-info", response_model=CollateralScoreModelInfo)
def get_info():
    """스코어링 모델이 어떤 데이터를 얼마나, 어떻게 학습했는지 투명하게 보여준다."""

    return CollateralScoreModelInfo(**get_model_info())
