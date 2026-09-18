"""국토교통부 실거래가 API 호출에 필요한 법정동코드(시군구 단위, 5자리) 매핑.

전체 법정동코드는 행정표준코드관리시스템(www.code.go.kr)에서 받을 수 있다.
MVP 단계에서는 샘플 데이터에 쓰인 지역만 등록해두고 필요할 때마다 추가한다.
"""


class LawdCodeNotFoundError(Exception):
    pass


LAWD_CODES: dict[tuple[str, str], str] = {
    ("서울특별시", "강남구"): "11680",
    ("서울특별시", "서초구"): "11650",
    ("서울특별시", "마포구"): "11440",
    ("경기도", "성남시 분당구"): "41135",
    ("경기도", "수원시 영통구"): "41117",
}


def get_lawd_cd(sido: str, sigungu: str) -> str:
    code = LAWD_CODES.get((sido, sigungu))
    if code is None:
        raise LawdCodeNotFoundError(
            f"'{sido} {sigungu}'에 대한 법정동코드가 등록되어 있지 않습니다. "
            "app/services/external/lawd_codes.py 의 LAWD_CODES에 코드를 추가해주세요."
        )
    return code
