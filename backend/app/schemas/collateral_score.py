from pydantic import BaseModel


class CollateralScoreTrainResult(BaseModel):
    n_rows: int
    trained_at: str
    source_breakdown: dict[str, int]
    feature_importances: dict[str, float]
    mae: float
    rmse: float
    r2: float


class CollateralScoreModelInfo(BaseModel):
    is_available: bool
    n_rows: int
    source_breakdown: dict[str, int]
    trained_at: str | None
    metrics: dict[str, float]
    feature_importances: dict[str, float]
    feature_descriptions: dict[str, str]
    target_description: str
