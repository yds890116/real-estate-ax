"""market_transactions(국토부 API로 수집된 실거래가)로 XGBoost 시세 추정 모델을 학습한다."""

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session
from xgboost import XGBRegressor

from app.models.market_transaction import MarketTransaction

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "valuation_xgb.joblib"

BASE_YEAR = 2020  # time_index 계산 기준연도
MIN_TRAINING_ROWS = 200
FEATURE_COLS = ["region", "exclusive_area", "floor", "build_age", "time_index"]


class TrainingDataError(Exception):
    pass


def _build_training_frame(db: Session) -> pd.DataFrame:
    rows = db.query(MarketTransaction).all()

    records = []
    for r in rows:
        if r.floor is None or r.build_year is None:
            continue
        deal_year, deal_month = int(r.deal_date[:4]), int(r.deal_date[5:7])
        records.append(
            {
                "region": f"{r.sido}_{r.sigungu}",
                "exclusive_area": r.exclusive_area,
                "floor": r.floor,
                "build_age": deal_year - r.build_year,
                "time_index": (deal_year - BASE_YEAR) * 12 + deal_month,
                "deal_year": deal_year,
                "deal_month": deal_month,
                "deal_price": r.deal_price,
            }
        )

    if len(records) < MIN_TRAINING_ROWS:
        raise TrainingDataError(
            f"학습 데이터가 부족합니다 (정제 후 {len(records)}건, 최소 {MIN_TRAINING_ROWS}건 필요). "
            "market-data/ingest로 더 많은 지역/기간을 수집해주세요."
        )

    df = pd.DataFrame(records)
    df["region"] = df["region"].astype("category")
    return df


def train_valuation_model(db: Session) -> dict:
    df = _build_training_frame(db)

    X = df[FEATURE_COLS]
    y = df["deal_price"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        tree_method="hist",
        enable_categorical=True,
        random_state=42,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
        "r2": float(r2_score(y_test, pred)),
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_cols": FEATURE_COLS,
        "known_regions": sorted(df["region"].cat.categories.tolist()),
        "region_counts": df["region"].value_counts().to_dict(),
        "metrics": metrics,
        "n_rows": len(df),
        "base_year": BASE_YEAR,
        "latest_deal_year": int(df["deal_year"].max()),
        "latest_deal_month": int(df.loc[df["deal_year"] == df["deal_year"].max(), "deal_month"].max()),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(bundle, ARTIFACT_PATH)

    return {
        "n_rows": bundle["n_rows"],
        "trained_at": bundle["trained_at"],
        **metrics,
    }
