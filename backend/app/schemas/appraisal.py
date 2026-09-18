from pydantic import BaseModel, ConfigDict


class AppraisalCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_file: str
    case_type: str
    sido: str | None
    sigungu: str | None
    dong: str
    jibun: str | None
    complex_name: str
    dong_ho: str | None
    usage: str
    exclusive_area: float
    event_date: str
    purpose: str | None
    amount: int  # 만원
    unit_price: int  # 만원/㎡
    location_note: str | None
    approval_date: str | None
    similarity: float | None = None  # 검색 결과에서만 채워짐 (0~1)


class AppraisalIngestResult(BaseModel):
    files_found: int
    files_parsed: int
    files_failed: list[dict]
    cases_inserted: int
    cases_skipped_duplicate: int


class AppraisalSearchRequest(BaseModel):
    sido: str
    sigungu: str
    dong: str | None = None
    usage: str = "아파트"
    exclusive_area: float
    top_k: int = 5


class AppraisalSearchResult(BaseModel):
    cases: list[AppraisalCaseResponse]
    reference_price_per_area: int | None  # 만원/㎡, 유사사례 가중평균
    reference_price: int | None  # 만원, reference_price_per_area * exclusive_area
    reference_area: float | None = None  # 참고 기준 전용면적(㎡). 실거래 기반일 때는 단지 내 최소 평형.
    explanation: str
    generation_method: str  # "llm" | "template"
    disclaimer: str = "본 참고 감정가는 AI가 유사사례를 기반으로 산출한 추정치이며, 실제 감정평가는 감정평가사의 고유 업무로 차이가 있을 수 있습니다."
