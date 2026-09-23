from pydantic import BaseModel


class AutocompleteSuggestionResponse(BaseModel):
    place_name: str
    address_name: str
    road_address_name: str | None
    x: str
    y: str
    category_group_name: str | None
