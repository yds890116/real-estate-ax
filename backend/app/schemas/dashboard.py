from datetime import datetime

from pydantic import BaseModel


class DashboardItem(BaseModel):
    property_id: int
    address: str
    sido: str
    sigungu: str
    property_type: str
    exclusive_area: float

    estimated_price: int
    price_per_area: int
    risk_grade: int
    risk_level_label: str

    has_registry: bool
    registry_risk_count: int

    reference_price: int | None
    price_gap_ratio: float | None  # (reference_price - estimated_price) / estimated_price

    opinion_status: str  # "none" | "draft" | "edited"

    alerts: list[str]
    created_at: datetime
