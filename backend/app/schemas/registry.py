from pydantic import BaseModel, ConfigDict


class RegistryRight(BaseModel):
    section: str  # "갑구" | "을구"
    rank: str | None = None  # 순위번호
    right_type: str  # 근저당권설정, 가압류, 가등기, 전세권설정 등
    holder: str | None = None  # 채권자/권리자
    amount: int | None = None  # 채권최고액 등 (만원)
    registered_date: str | None = None
    raw_text: str  # 원문 일부 (검증용)


class RegistryAnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int | None
    filename: str
    rights: list[RegistryRight]
    risk_flags: list[str]
    summary: str
    generation_method: str  # "llm" | "template"
    mortgage_total: int | None = None  # 근저당권 채권최고액 합계 (만원)
    estimated_price: int | None = None  # 연결된 물건의 AI 추정시세 (만원, 물건 연결 시에만)
    disclaimer: str = "본 권리분석은 AI 참고용이며 최종 판단은 전문가(법무사·변호사) 검토가 필요합니다."
