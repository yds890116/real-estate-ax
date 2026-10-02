from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    PROJECT_NAME: str = "부동산 시세·권리·리스크 통합관리 시스템"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = f"sqlite:///{(BASE_DIR.parent / 'data' / 'realestate.db').as_posix()}"
    SAMPLE_DATA_DIR: Path = BASE_DIR.parent / "data" / "sample"
    APPRAISAL_SAMPLE_DIR: Path = BASE_DIR.parent / "sample" / "감정평가서"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 공공데이터포털 국토교통부_아파트 매매 실거래가 상세자료 서비스키 (URL 인코딩된 형태)
    MOLIT_SERVICE_KEY: str = ""

    # 등기부등본 권리분석 요약 생성용 (미설정 시 템플릿 기반 요약으로 자동 폴백)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5"

    # 카카오맵 주소/키워드 검색 (주소·단지명 → 좌표·법정동코드 변환용)
    KAKAO_REST_API_KEY: str = ""

    # 국토교통부 공간정보 오픈플랫폼 브이월드(V-World) - 지목/용도지역/개별공시지가 등 토지특성 조회
    # https://www.vworld.kr/dev/ 회원가입 후 "오픈API 인증키 발급" 메뉴에서 발급
    VWORLD_API_KEY: str = ""
    # 발급 시 등록한 서비스 도메인(인증키가 그 도메인에서의 요청만 허용) - 로컬 개발 기본값은 localhost
    VWORLD_DOMAIN: str = "localhost"

    # 한국자산관리공사 온비드 공공데이터포털 서비스키 (MOLIT_SERVICE_KEY와 동일 계정 키를 공유 사용 가능)
    ONBID_SERVICE_KEY: str = ""

    # 한국자산관리공사_차세대 온비드 지역별 입찰 통계 조회서비스 (data.go.kr 15157756) 인증키
    ONBID_STATS_API_KEY: str = ""

    # data.go.kr 15157756 상세기능정보 탭(로그인 필요)이 렌더링되지 않아 서비스/기능(오퍼레이션)명을
    # 확정하지 못했다. KAMCO 명명 규칙(UtlinsttPblsalThingInquireSvc 등) 기반의 잠정값이며,
    # 실제 활용가이드 문서 확인 후 .env에서 교체하면 코드 수정 없이 바로 반영된다.
    ONBID_STATS_SERVICE: str = "UtlinsttPbctSttusInquireSvc"
    ONBID_STATS_FUNCTION: str = "getUtlinsttPbctRgnSttus"

    # 네이버 뉴스 검색 API (개발자센터 developers.naver.com 애플리케이션 등록 필요)
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # 데이터 수집 배치 스케줄 (새벽 시간대, 24시간제 시:분)
    BATCH_SCHEDULE_HOUR: int = 3
    BATCH_SCHEDULE_MINUTE: int = 0

    # 지역별 입찰 통계는 갱신 주기가 느려(월 단위 집계) 주 1회만 수집한다. cron day_of_week: mon=0 ... sun=6
    ONBID_STATS_SCHEDULE_DAY_OF_WEEK: int = 0
    ONBID_STATS_SCHEDULE_HOUR: int = 4
    ONBID_STATS_SCHEDULE_MINUTE: int = 0

    # 한국부동산원 R-ONE 부동산통계정보 Open API (https://www.reb.or.kr/r-one)
    RONE_API_KEY: str = ""

    # 지역별 공동주택 실거래가격지수/매매·전세가격지수는 월 단위 집계 통계라 매월 1회만 수집한다.
    RONE_SCHEDULE_DAY: int = 1
    RONE_SCHEDULE_HOUR: int = 5
    RONE_SCHEDULE_MINUTE: int = 0

    # KB부동산 데이터허브 주택가격동향조사(매매/전세/월세 가격지수)도 월 단위 집계라 매월 1회만 수집한다.
    KB_STATS_SCHEDULE_DAY: int = 1
    KB_STATS_SCHEDULE_HOUR: int = 5
    KB_STATS_SCHEDULE_MINUTE: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
