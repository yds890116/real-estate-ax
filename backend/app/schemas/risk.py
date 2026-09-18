from pydantic import BaseModel

from app.schemas.property import PropertyBase
from app.schemas.valuation import ValuationResult


class RiskScoreRequest(BaseModel):
    property_id: int | None = None
    property: PropertyBase | None = None
    valuation: ValuationResult | None = None  # 없으면 서버에서 내부적으로 재계산


class RiskFactor(BaseModel):
    name: str
    description: str
    impact: str  # "positive" | "negative" | "neutral"
    weight: float
    method: str = "rule"  # "rule" | "ml" — 규칙 기반인지 학습된 모델 기반인지


class RiskIndicator(BaseModel):
    key: str
    label: str
    description: str  # 사람이 읽을 수 있는 원본 값 설명 (예: "변동계수 12.3% (18건)")
    normalized_score: float  # 0~100, 높을수록 고위험
    weight: float  # 카테고리 내 가중치
    method: str  # "rule" | "ml"
    available: bool = True  # 데이터 부족으로 중립값을 쓴 경우 False


class RiskCategory(BaseModel):
    key: str
    label: str
    weight: float  # 전체 카테고리 가중치
    normalized_score: float  # 0~100, 하위 지표 가중합
    contribution: float  # weight * normalized_score (종합점수 100점 중 이 카테고리의 기여도)
    indicators: list[RiskIndicator]


class RiskScoreResult(BaseModel):
    risk_grade: int  # 1(안전) ~ 10(고위험)
    risk_level_label: str  # 안전/양호/주의/위험 등
    grade_tier: str  # "상" | "중" | "하" — 종합점수 기반 3단계 등급 (v2)
    score: float  # 0~100 종합점수 (카테고리 가중합)
    model_version: str
    categories: list[RiskCategory]  # v2: 카테고리별 지표·기여도 breakdown
    factors: list[RiskFactor]  # 카테고리별 요약 (기존 UI 호환용)
    disclaimer: str = "본 리스크 등급은 AI 참고 지표이며 최종 담보 판단은 심사역 검토가 필요합니다."
