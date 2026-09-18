from pydantic import BaseModel

from app.schemas.property import PropertyBase


class ValuationRequest(BaseModel):
    """property_id가 있으면 DB에서 조회, 없으면 property 필드로 즉석 추정."""

    property_id: int | None = None
    property: PropertyBase | None = None


class ValuationResult(BaseModel):
    estimated_price: int  # 만원 단위
    price_lower: int
    price_upper: int
    confidence_level: float  # 0~1
    price_per_area: int  # 만원/m2
    comparable_count: int
    model_version: str
    disclaimer: str = "본 추정 시세는 AI 참고용이며 실제 감정평가·시세와 차이가 있을 수 있습니다."


class ValuationModelTrainResult(BaseModel):
    n_rows: int
    trained_at: str
    mae: float
    rmse: float
    r2: float
