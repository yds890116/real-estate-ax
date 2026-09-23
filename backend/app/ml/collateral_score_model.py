"""학습된 담보 스코어링 XGBoost 모델을 로드해 예측을 제공하는 래퍼.

학습되지 않았으면(artifact 없음) is_available이 False를 반환하고, 호출 측
(collateral_scoring_service.py)은 규칙 기반 점수로 폴백한다.
"""

from pathlib import Path

import pandas as pd

from app.ml.collateral_score_train import ARTIFACT_PATH, FEATURE_COLS


class CollateralScoreModel:
    def __init__(self, artifact_path: Path = ARTIFACT_PATH):
        self.artifact_path = artifact_path
        self.model = None
        self.known_categories: dict[str, list[str]] = {}
        self.metrics: dict[str, float] = {}
        self.feature_importances: dict[str, float] = {}
        self.n_rows = 0
        self.source_breakdown: dict[str, int] = {}
        self.trained_at: str | None = None
        self.reload()

    def reload(self) -> None:
        if not self.artifact_path.exists():
            self.model = None
            return

        import joblib

        bundle = joblib.load(self.artifact_path)
        self.model = bundle["model"]
        self.known_categories = bundle["known_categories"]
        self.metrics = bundle["metrics"]
        self.feature_importances = bundle["feature_importances"]
        self.n_rows = bundle["n_rows"]
        self.source_breakdown = bundle["source_breakdown"]
        self.trained_at = bundle["trained_at"]

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def predict_uscbd_cnt(
        self,
        ctgr_full_nm: str | None,
        sido: str | None,
        dpsl_mtd_nm: str | None,
        appraisal_amt: int,
        min_bid_prc: int,
        fee_rate_pct: float,
    ) -> float:
        def _known(col: str, value: str | None) -> str:
            categories = self.known_categories.get(col, [])
            return value if value in categories else (categories[0] if categories else "미상")

        row = pd.DataFrame(
            [
                {
                    "ctgr_full_nm": _known("ctgr_full_nm", ctgr_full_nm),
                    "sido": _known("sido", sido),
                    "dpsl_mtd_nm": _known("dpsl_mtd_nm", dpsl_mtd_nm),
                    "appraisal_amt": appraisal_amt,
                    "min_bid_prc": min_bid_prc,
                    "fee_rate_pct": fee_rate_pct,
                }
            ]
        )
        for col in ("ctgr_full_nm", "sido", "dpsl_mtd_nm"):
            row[col] = pd.Categorical([row[col].iloc[0]], categories=self.known_categories.get(col, [row[col].iloc[0]]))
        row = row[FEATURE_COLS]

        return max(0.0, float(self.model.predict(row)[0]))


collateral_score_model = CollateralScoreModel()
