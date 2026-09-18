"""시세 추정 엔진.

1순위: 학습된 XGBoost 모델(app/ml)이 있고 해당 지역이 학습 데이터에 포함돼 있으면 이를 사용.
2순위: market_transactions에 국토부 API로 수집된 실거래가 비교사례가 충분하면 유사거래 평균단가 규칙 기반 추정.
3순위: 그마저도 없으면 data/sample/transactions_sample.csv 더미 데이터로 폴백.

각 단계는 ValuationResult.model_version에 어떤 경로로 계산됐는지 표시한다.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.valuation_model import xgb_valuation_model
from app.models.market_transaction import MarketTransaction
from app.schemas.property import PropertyBase
from app.schemas.valuation import ValuationResult

MODEL_VERSION = "rule-based-v0"
MIN_LIVE_COMPARABLES = 2


class ValuationEngine:
    def __init__(self, sample_csv_path: Path | None = None):
        csv_path = sample_csv_path or (settings.SAMPLE_DATA_DIR / "transactions_sample.csv")
        self._sample_transactions = pd.read_csv(csv_path)
        self._sample_transactions["price_per_area"] = (
            self._sample_transactions["deal_price"] / self._sample_transactions["exclusive_area"]
        )

    @staticmethod
    def _area_filter(df: pd.DataFrame, prop: PropertyBase) -> pd.DataFrame:
        return df[
            (df["exclusive_area"] >= prop.exclusive_area * 0.7)
            & (df["exclusive_area"] <= prop.exclusive_area * 1.3)
        ]

    @staticmethod
    def _load_live_transactions(db: Session, prop: PropertyBase) -> pd.DataFrame:
        rows = (
            db.query(MarketTransaction)
            .filter(
                MarketTransaction.sido == prop.sido,
                MarketTransaction.sigungu == prop.sigungu,
            )
            .all()
        )
        if not rows:
            return pd.DataFrame(columns=["exclusive_area", "deal_price", "price_per_area"])

        df = pd.DataFrame(
            [
                {"exclusive_area": r.exclusive_area, "deal_price": r.deal_price}
                for r in rows
            ]
        )
        df["price_per_area"] = df["deal_price"] / df["exclusive_area"]
        return df

    def _find_sample_comparables(self, prop: PropertyBase) -> pd.DataFrame:
        df = self._sample_transactions

        same_sigungu = df[(df["sido"] == prop.sido) & (df["sigungu"] == prop.sigungu)]
        area_filtered = self._area_filter(same_sigungu, prop)
        if len(area_filtered) >= MIN_LIVE_COMPARABLES:
            return area_filtered
        if len(same_sigungu) >= 1:
            return same_sigungu

        same_sido = df[df["sido"] == prop.sido]
        if len(same_sido) >= 1:
            return same_sido

        return df

    def _find_comparables(self, prop: PropertyBase, db: Session | None) -> tuple[pd.DataFrame, str]:
        if db is not None:
            live_df = self._load_live_transactions(db, prop)
            live_area_filtered = self._area_filter(live_df, prop)
            if len(live_area_filtered) >= MIN_LIVE_COMPARABLES:
                return live_area_filtered, "live"

        return self._find_sample_comparables(prop), "sample"

    def estimate(self, prop: PropertyBase, db: Session | None = None) -> ValuationResult:
        if xgb_valuation_model.is_available and xgb_valuation_model.region_known(prop.sido, prop.sigungu):
            return self._estimate_with_ml(prop)

        return self._estimate_with_rules(prop, db)

    def _estimate_with_ml(self, prop: PropertyBase) -> ValuationResult:
        point_estimate = xgb_valuation_model.predict(prop)
        rmse = xgb_valuation_model.metrics.get("rmse", point_estimate * 0.1)
        r2 = xgb_valuation_model.metrics.get("r2", 0.5)

        spread_ratio = min(max(rmse / point_estimate, 0.03), 0.25) if point_estimate else 0.15
        confidence_level = max(0.5, min(0.95, r2))
        region_count = xgb_valuation_model.region_counts.get(f"{prop.sido}_{prop.sigungu}", xgb_valuation_model.n_rows)
        trained_date = (xgb_valuation_model.trained_at or "")[:10]

        return ValuationResult(
            estimated_price=round(point_estimate),
            price_lower=round(point_estimate * (1 - spread_ratio)),
            price_upper=round(point_estimate * (1 + spread_ratio)),
            confidence_level=round(confidence_level, 2),
            price_per_area=round(point_estimate / prop.exclusive_area) if prop.exclusive_area else 0,
            comparable_count=region_count,
            model_version=f"xgboost-v1(n={xgb_valuation_model.n_rows},trained={trained_date})",
        )

    def _estimate_with_rules(self, prop: PropertyBase, db: Session | None) -> ValuationResult:
        comparables, data_source = self._find_comparables(prop, db)

        base_unit_price = float(comparables["price_per_area"].mean())

        # 층수/준공연도 보정 (단순 휴리스틱)
        floor_adj = 1.0
        if prop.floor is not None and prop.total_floors and prop.total_floors > 0:
            relative_floor = prop.floor / prop.total_floors
            if relative_floor <= 0.15:
                floor_adj = 0.97  # 저층 감가
            elif relative_floor >= 0.8:
                floor_adj = 1.02  # 고층 프리미엄

        age_adj = 1.0
        if prop.build_year is not None:
            age = max(0, 2026 - prop.build_year)
            age_adj = max(0.85, 1 - age * 0.003)

        adjusted_unit_price = base_unit_price * floor_adj * age_adj
        estimated_price = adjusted_unit_price * prop.exclusive_area

        comparable_count = int(len(comparables))
        std_ratio = float(comparables["price_per_area"].std() or 0) / base_unit_price if base_unit_price else 0.1
        spread_ratio = min(max(std_ratio, 0.03), 0.15) if comparable_count > 1 else 0.15

        confidence_level = min(0.9, 0.5 + comparable_count * 0.05)

        return ValuationResult(
            estimated_price=round(estimated_price),
            price_lower=round(estimated_price * (1 - spread_ratio)),
            price_upper=round(estimated_price * (1 + spread_ratio)),
            confidence_level=round(confidence_level, 2),
            price_per_area=round(adjusted_unit_price),
            comparable_count=comparable_count,
            model_version=f"{MODEL_VERSION}+{data_source}",
        )


valuation_engine = ValuationEngine()
