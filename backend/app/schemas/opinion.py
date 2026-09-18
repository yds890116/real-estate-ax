from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OpinionEditHistoryEntry(BaseModel):
    content: str
    saved_at: str


class ReviewOpinionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    ai_draft: str
    current_content: str
    edit_history: list[OpinionEditHistoryEntry]
    generation_method: str  # "llm" | "template"
    created_at: datetime
    updated_at: datetime
    disclaimer: str = "본 심사의견 초안은 AI가 생성한 참고용 자료이며, 최종 심사의견은 심사역의 검토·확정이 필요합니다."


class OpinionUpdateRequest(BaseModel):
    content: str
