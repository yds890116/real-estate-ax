from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PropertyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str
    sido: str
    sigungu: str
    dong: str | None = None

    property_type: str
    complex_name: str | None = None

    exclusive_area: float
    floor: int | None = None
    total_floors: int | None = None
    build_year: int | None = None
    household_count: int | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(PropertyBase):
    id: int
    created_at: datetime
