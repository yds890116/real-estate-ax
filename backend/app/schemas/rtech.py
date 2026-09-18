from pydantic import BaseModel


class RtechDongCollectResult(BaseModel):
    dong_name: str
    complex_count: int
    collected: int
    skipped: int
    failed: int
    status: str
    error: str | None = None


class RtechAreaComparisonItem(BaseModel):
    priv_area: float
    pyong: float
    rtech_base_date: str
    rtech_sale_lower_price: int | None
    rtech_sale_upper_price: int | None
    rtech_jeonse_lower_price: int | None
    rtech_jeonse_upper_price: int | None
    molit_sale_avg_price: int | None
    molit_sale_count: int
    molit_jeonse_avg_price: int | None
    molit_jeonse_count: int
    gap_ratio_sale_pct: float | None


class RtechRealTransactionItem(BaseModel):
    trade_mode: str
    deal_ymd: str
    deal_amount: int
    area: float


class RtechComparisonResult(BaseModel):
    complex_name: str
    sigungu: str
    address: str | None
    household_count: int | None
    items: list[RtechAreaComparisonItem]
    rtech_real_transactions: list[RtechRealTransactionItem]
