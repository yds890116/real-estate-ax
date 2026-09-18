from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.property import Property
from app.schemas.property import PropertyBase


def resolve_property(
    db: Session,
    property_id: int | None,
    property_payload: PropertyBase | None,
) -> PropertyBase:
    """요청에서 property_id 또는 인라인 property 중 하나로 대상 물건을 확정한다."""

    if property_id is not None:
        db_property = db.get(Property, property_id)
        if db_property is None:
            raise HTTPException(status_code=404, detail="Property not found")
        return PropertyBase.model_validate(db_property)

    if property_payload is not None:
        return property_payload

    raise HTTPException(status_code=400, detail="property_id 또는 property 중 하나는 필수입니다.")
