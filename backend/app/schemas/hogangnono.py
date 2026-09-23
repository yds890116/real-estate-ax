from pydantic import BaseModel


class HogangnonoAreaPrice(BaseModel):
    area_no: int
    private_area: float  # 전용면적 ㎡
    real_trade_price: int | None  # 최근 실거래가(매매), 만원
    portal_trade_price: int | None  # 포털 시세(매매), 만원
    real_rent_price: int | None  # 최근 실거래가(전세), 만원
    portal_rent_price: int | None  # 포털 시세(전세), 만원


class HogangnonoListingItem(BaseModel):
    item_id: int
    trade_type: str  # "매매" | "전세" | "월세"
    price: int  # 만원 - 매매가 / 전세보증금 / 월세보증금
    monthly_rent: int | None  # 만원, 월세일 때만 값 존재
    private_area: float  # 전용면적 ㎡
    public_area: float | None  # 공급면적 ㎡
    floor_tier: str | None  # "저"/"중"/"고"
    dong_name: str | None
    room_type: str | None  # 평형 타입 코드 (예: "113A")
    title: str | None


class HogangnonoComplexResult(BaseModel):
    found: bool
    complex_name: str | None = None
    address: str | None = None
    road_address: str | None = None
    total_household: int | None = None
    areas: list[HogangnonoAreaPrice] = []
    listings: list[HogangnonoListingItem] = []
    source: str = "hogangnono"
    notice: str | None = None
