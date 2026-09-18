"""학습된 XGBoost 시세 추정 모델을 로드해 예측을 제공하는 래퍼.

학습되지 않았거나(artifact 없음) 요청 지역이 학습 데이터에 없으면 is_available/region_known이
False를 반환하고, 호출 측(ValuationEngine)은 규칙 기반 로직으로 폴백한다.
"""

from pathlib import Path

import joblib
import pandas as pd

from app.ml.train import ARTIFACT_PATH
from app.schemas.property import PropertyBase


class XGBValuationModel:
    def __init__(self, artifact_path: Path = ARTIFACT_PATH):
        self.artifact_path = artifact_path
        self.model = None
        self.known_regions: set[str] = set()
        self.region_counts: dict[str, int] = {}
        self.metrics: dict[str, float] = {}
        self.n_rows = 0
        self.trained_at: str | None = None
        self.base_year = 2020
        self.latest_deal_year = 2024
        self.latest_deal_month = 1
        self.reload()

    def reload(self) -> None:
        if not self.artifact_path.exists():
            self.model = None
            return

        bundle = joblib.load(self.artifact_path)
        self.model = bundle["model"]
        self.known_regions = set(bundle["known_regions"])
        self.region_counts = bundle["region_counts"]
        self.metrics = bundle["metrics"]
        self.n_rows = bundle["n_rows"]
        self.trained_at = bundle["trained_at"]
        self.base_year = bundle["base_year"]
        self.latest_deal_year = bundle["latest_deal_year"]
        self.latest_deal_month = bundle["latest_deal_month"]

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def region_known(self, sido: str, sigungu: str) -> bool:
        return f"{sido}_{sigungu}" in self.known_regions

    def predict(self, prop: PropertyBase) -> float:
        """학습 데이터 중 가장 최근 거래시점을 기준으로 예측한다 (미래로의 무리한 외삽 방지)."""

        region = f"{prop.sido}_{prop.sigungu}"
        build_age = (self.latest_deal_year - prop.build_year) if prop.build_year else 15
        time_index = (self.latest_deal_year - self.base_year) * 12 + self.latest_deal_month

        row = pd.DataFrame(
            [
                {
                    "region": region,
                    "exclusive_area": prop.exclusive_area,
                    "floor": prop.floor if prop.floor is not None else 10,
                    "build_age": build_age,
                    "time_index": time_index,
                }
            ]
        )
        row["region"] = pd.Categorical([region], categories=sorted(self.known_regions))

        return float(self.model.predict(row)[0])


xgb_valuation_model = XGBValuationModel()
