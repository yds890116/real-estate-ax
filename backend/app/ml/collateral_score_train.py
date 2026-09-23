"""onbid_auction_items(온비드 공매 물건)로 담보 리스크 스코어링용 XGBoost 모델을 학습한다.

예측 타깃은 유찰횟수(uscbd_cnt) - 실제 최종 낙찰가를 수집하지 않으므로(온비드 API가 물건
목록 단계에서 낙찰결과까지 주지 않음) 이용 가능한 데이터 중 "이 물건이 팔리기 어려운
정도(유동성 리스크)"를 가장 직접적으로 나타내는 값을 학습 타깃으로 삼았다. 예측된 유찰횟수를
0~100점으로 환산해 risk_engine.py와 동일한 1~10등급 체계로 변환한다(app/services/
collateral_scoring_service.py).

이 개발 환경은 openapi.onbid.co.kr이 막혀 있어 실제 수집 데이터가 없으므로, 처음에는
app/services/onbid_auction_sample.py가 만든 샘플 데이터로 학습된다 - source 컬럼으로 실제
수집분과 샘플을 구분하며, model-info API가 이 구성비를 그대로 노출해 투명하게 알 수 있다.
"""

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session
from xgboost import XGBRegressor

from app.models.onbid_auction_item import OnbidAuctionItem

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "collateral_score_xgb.joblib"

MIN_TRAINING_ROWS = 50
FEATURE_COLS = ["ctgr_full_nm", "sido", "dpsl_mtd_nm", "appraisal_amt", "min_bid_prc", "fee_rate_pct"]


class TrainingDataError(Exception):
    pass


def _parse_sido(ldnm_adrs: str | None) -> str:
    if not ldnm_adrs:
        return "미상"
    return ldnm_adrs.split(" ")[0] or "미상"


def _parse_fee_rate(fee_rate: str | None) -> float | None:
    if not fee_rate:
        return None
    try:
        return float(fee_rate.replace("%", "").strip())
    except ValueError:
        return None


def _build_training_frame(db: Session) -> tuple[pd.DataFrame, dict[str, int]]:
    rows = db.query(OnbidAuctionItem).all()

    records = []
    for r in rows:
        if r.uscbd_cnt is None or r.apsl_ases_avg_amt is None or r.min_bid_prc is None:
            continue
        fee_rate_pct = _parse_fee_rate(r.fee_rate)
        if fee_rate_pct is None:
            continue
        records.append(
            {
                "ctgr_full_nm": r.ctgr_full_nm or "미상",
                "sido": _parse_sido(r.ldnm_adrs),
                "dpsl_mtd_nm": r.dpsl_mtd_nm or "미상",
                "appraisal_amt": r.apsl_ases_avg_amt,
                "min_bid_prc": r.min_bid_prc,
                "fee_rate_pct": fee_rate_pct,
                "uscbd_cnt": r.uscbd_cnt,
                "source": r.source,
            }
        )

    if len(records) < MIN_TRAINING_ROWS:
        raise TrainingDataError(
            f"학습 데이터가 부족합니다 (정제 후 {len(records)}건, 최소 {MIN_TRAINING_ROWS}건 필요). "
            "온비드 수집 배치를 먼저 실행해주세요."
        )

    df = pd.DataFrame(records)
    source_breakdown = df["source"].value_counts().to_dict()
    for col in ("ctgr_full_nm", "sido", "dpsl_mtd_nm"):
        df[col] = df[col].astype("category")
    return df, source_breakdown


def train_collateral_score_model(db: Session) -> dict:
    df, source_breakdown = _build_training_frame(db)

    X = df[FEATURE_COLS]
    y = df["uscbd_cnt"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
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

    importances = {col: float(imp) for col, imp in zip(FEATURE_COLS, model.feature_importances_)}

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_cols": FEATURE_COLS,
        "known_categories": {col: sorted(df[col].cat.categories.tolist()) for col in ("ctgr_full_nm", "sido", "dpsl_mtd_nm")},
        "metrics": metrics,
        "feature_importances": importances,
        "n_rows": len(df),
        "source_breakdown": source_breakdown,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(bundle, ARTIFACT_PATH)

    return {
        "n_rows": bundle["n_rows"],
        "trained_at": bundle["trained_at"],
        "source_breakdown": source_breakdown,
        "feature_importances": importances,
        **metrics,
    }
