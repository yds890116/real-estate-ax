"""경매/공매 물건의 담보 스코어링(1~10등급, 낮을수록 안전) 서비스.

ML(우선) + 규칙(폴백) 하이브리드로, app/services/risk_engine.py와 동일한 1~10등급/5단계
라벨 체계를 쓴다. 예측 대상은 "이 물건이 앞으로 유찰을 몇 번이나 거칠 것인가"(유동성 리스크의
직접적인 대리 지표)이며, 신규 등록 물건(아직 유찰 이력이 없는 물건)에 대한 사전 위험 신호로
쓰기 위한 것이다 - 이미 여러 번 유찰된 물건은 그 자체로 이미 위험 신호(uscbd_cnt)가 있으므로
예측보다 관측값을 그대로 우선한다.
"""

from app.ml.collateral_score_model import collateral_score_model
from app.models.onbid_auction_item import OnbidAuctionItem

RISK_LEVEL_LABELS = {
    range(1, 3): "안전",
    range(3, 5): "양호",
    range(5, 7): "주의",
    range(7, 9): "위험",
    range(9, 11): "고위험",
}


def _grade_label(grade: int) -> str:
    for grade_range, label in RISK_LEVEL_LABELS.items():
        if grade in grade_range:
            return label
    return "미분류"


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


def _score_to_grade(score: float) -> int:
    return max(1, min(10, round(score / 10) or 1))


def score_item(item: OnbidAuctionItem) -> dict:
    fee_rate_pct = _parse_fee_rate(item.fee_rate)
    observed_uscbd = item.uscbd_cnt or 0

    if collateral_score_model.is_available and item.apsl_ases_avg_amt and item.min_bid_prc and fee_rate_pct is not None:
        predicted_uscbd = collateral_score_model.predict_uscbd_cnt(
            ctgr_full_nm=item.ctgr_full_nm,
            sido=_parse_sido(item.ldnm_adrs),
            dpsl_mtd_nm=item.dpsl_mtd_nm,
            appraisal_amt=item.apsl_ases_avg_amt,
            min_bid_prc=item.min_bid_prc,
            fee_rate_pct=fee_rate_pct,
        )
        # 이미 관측된 유찰횟수가 예측치보다 크면(이미 여러 번 유찰된 물건) 관측값을 우선한다.
        effective_uscbd = max(predicted_uscbd, observed_uscbd)
        score = min(100.0, effective_uscbd * 25)
        method = "ml"
    else:
        # 모델 미학습 시 폴백: 최저입찰가율이 낮을수록(이미 많이 저감됐을수록) 위험 신호로 본다.
        base = fee_rate_pct if fee_rate_pct is not None else 100.0
        score = min(100.0, max(0.0, (100 - base) * 1.5 + observed_uscbd * 15))
        method = "rule"

    grade = _score_to_grade(score)

    return {
        "score": round(score, 1),
        "grade": grade,
        "grade_label": _grade_label(grade),
        "method": method,
        "observed_uscbd_cnt": observed_uscbd,
    }


def get_model_info() -> dict:
    """스코어링 모델 투명성 화면용 - 학습에 어떤 데이터를 어떻게 썼는지 그대로 노출한다."""

    return {
        "is_available": collateral_score_model.is_available,
        "n_rows": collateral_score_model.n_rows,
        "source_breakdown": collateral_score_model.source_breakdown,
        "trained_at": collateral_score_model.trained_at,
        "metrics": collateral_score_model.metrics,
        "feature_importances": collateral_score_model.feature_importances,
        "feature_descriptions": {
            "ctgr_full_nm": "물건 용도(아파트/오피스텔/상가/토지 등)",
            "sido": "소재지 시도",
            "dpsl_mtd_nm": "처분방식(매각/임대)",
            "appraisal_amt": "감정가(원)",
            "min_bid_prc": "최저입찰가(원)",
            "fee_rate_pct": "최저입찰가율(%, 감정가 대비)",
        },
        "target_description": "예측 대상: 유찰횟수(이 물건이 낙찰되기까지 유찰을 겪을 것으로 예상되는 횟수) - 값이 클수록 유동성 리스크가 높다고 본다.",
    }
