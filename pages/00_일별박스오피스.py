import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------

st.set_page_config(
    page_title="박스오피스 대시보드",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 어제의 박스오피스")


# ------------------------------------------------------------
# 2. KOBIS API 주소
# ------------------------------------------------------------

DAILY_BOXOFFICE_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

MOVIE_INFO_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "movie/searchMovieInfo.json"
)


# ------------------------------------------------------------
# 3. 인증키 확인
# ------------------------------------------------------------

try:
    KOBIS_KEY = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "KOBIS 인증키가 없습니다. "
        "Streamlit Cloud의 Secrets에 KOBIS_KEY를 등록해 주세요."
    )
    st.code(
        'KOBIS_KEY = "발급받은 인증키"',
        language="toml",
    )
    st.stop()


# ------------------------------------------------------------
# 4. 공통 API 요청 함수
# ------------------------------------------------------------

def request_kobis_json(
    url: str,
    params: dict,
    timeout: int = 15,
) -> dict:
    """
    KOBIS API를 호출하고 JSON 결과를 반환합니다.

    통신 실패, 잘못된 인증키, JSON 변환 실패를 한곳에서 처리합니다.
    """
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise RuntimeError(
            f"KOBIS 서버 요청 중 오류가 발생했습니다: {error}"
        ) from error

    try:
        data = response.json()

    except ValueError as error:
        raise RuntimeError(
            "KOBIS 서버 응답을 JSON으로 읽지 못했습니다."
        ) from error

    # KOBIS는 인증키 오류가 발생해도 상태코드 200을 줄 수 있습니다.
    if "faultInfo" in data:
        fault_message = data.get("faultInfo", {}).get(
            "message",
            "인증키 또는 요청 조건을 확인해 주세요.",
        )

        raise RuntimeError(
            f"KOBIS API 오류: {fault_message}"
        )

    return data


# ------------------------------------------------------------
# 5. 일별 박스오피스 조회
# ------------------------------------------------------------

@st.cache_data(
    show_spinner=False,
    ttl=60 * 30,
)
def load_daily_boxoffice(
    api_key: str,
    target_date: str,
) -> pd.DataFrame:
    """
    특정 날짜의 일별 박스오피스 TOP 10을 조회합니다.
    """
    data = request_kobis_json(
        DAILY_BOXOFFICE_URL,
        params={
            "key": api_key,
            "targetDt": target_date,
        },
    )

    boxoffice_result = data.get(
        "boxOfficeResult",
        {},
    )

    boxoffice_list = boxoffice_result.get(
        "dailyBoxOfficeList",
        [],
    )

    if not boxoffice_list:
        return pd.DataFrame()

    df = pd.DataFrame(boxoffice_list)

    # API에서 글자로 전달된 숫자를 실제 숫자로 바꿉니다.
    numeric_columns = [
        "rank",
        "rankInten",
        "salesAmt",
        "salesAcc",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "showCnt",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    return df


# ------------------------------------------------------------
# 6. 영화 상세정보에서 장르 조회
# ------------------------------------------------------------

@st.cache_data(
    show_spinner=False,
    ttl=60 * 60 * 24 * 7,
)
def load_movie_genres(
    api_key: str,
    movie_code: str,
) -> str:
    """
    영화코드로 영화 상세정보를 조회하고 장르를 반환합니다.

    영화 상세정보는 자주 바뀌지 않으므로 7일간 캐시합니다.
    """
    try:
        data = request_kobis_json(
            MOVIE_INFO_URL,
            params={
                "key": api_key,
                "movieCd": movie_code,
            },
        )

        movie_info = data.get(
            "movieInfoResult",
            {},
        ).get(
            "movieInfo",
            {},
        )

        genres = movie_info.get(
            "genres",
            [],
        )

        genre_names = [
            genre.get("genreNm", "").strip()
            for genre in genres
            if genre.get("genreNm", "").strip()
        ]

        if not genre_names:
            return "장르 정보 없음"

        return ", ".join(genre_names)

    except RuntimeError:
        # 특정 영화의 상세정보만 실패하더라도
        # 전체 대시보드가 멈추지 않도록 처리합니다.
        return "장르 정보 없음"


def add_genres_to_boxoffice(
    boxoffice_df: pd.DataFrame,
    api_key: str,
) -> pd.DataFrame:
    """
    박스오피스 영화마다 상세정보 API를 호출해 장르를 붙입니다.
    """
    df = boxoffice_df.copy()

    df["장르"] = df["movieCd"].apply(
        lambda movie_code: load_movie_genres(
            api_key,
            str(movie_code),
        )
    )

    return df


# ------------------------------------------------------------
# 7. 긴 영화 제목에 맞춰 글자 크기 결정
# ------------------------------------------------------------

def get_movie_title_font_size(movie_title: str) -> int:
    """
    영화 제목 길이에 따라 카드의 글자 크기를 조절합니다.

    제목이 짧으면 크게,
    제목이 길면 조금 작게 표시합니다.
    """
    title_length = len(str(movie_title))

    if title_length <= 8:
        return 34

    if title_length <= 14:
        return 29

    if title_length <= 20:
        return 25

    if title_length <= 28:
        return 22

    return 19


def render_top_movie_card(movie_title: str) -> None:
    """
    긴 영화 제목도 잘리지 않도록 직접 만든 카드를 표시합니다.
    """
    safe_title = html.escape(str(movie_title))
    font_size = get_movie_title_font_size(movie_title)

    card_html = f"""
<div class="top-movie-card">
    <div class="top-movie-label">어제 1위</div>
    <div class="top-movie-title" style="font-size:{font_size}px;">
        {safe_title}
    </div>
</div>
"""

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# 8. 화면 스타일
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    /*
    어제 1위 영화 카드입니다.
    제목이 길어도 말줄임표로 자르지 않고 여러 줄로 표시합니다.
    */
    .top-movie-card {
        min-height: 142px;
        padding: 18px 20px;
        border: 1px solid rgba(128, 128, 128, 0.28);
        border-radius: 12px;
        background: rgba(128, 128, 128, 0.06);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .top-movie-label {
        margin-bottom: 10px;
        font-size: 14px;
        color: rgba(128, 128, 128, 0.95);
    }

    .top-movie-title {
        width: 100%;
        font-weight: 700;
        line-height: 1.28;

        /* 긴 제목을 자르지 않고 줄바꿈합니다. */
        white-space: normal;
        overflow: visible;
        text-overflow: clip;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }

    /*
    작은 화면에서는 카드 제목을 조금 더 작게 표시합니다.
    */
    @media (max-width: 700px) {
        .top-movie-title {
            font-size: 20px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 9. 한국 시간 기준 조회 날짜 결정
# ------------------------------------------------------------

korea_now = datetime.now(
    ZoneInfo("Asia/Seoul")
)

yesterday = korea_now - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

st.caption(
    f"조회 기준일: {yesterday.strftime('%Y-%m-%d')} "
    f"· 한국 시간 기준 어제"
)


# ------------------------------------------------------------
# 10. 데이터 불러오기
# ------------------------------------------------------------

try:
    with st.spinner(
        "어제의 박스오피스와 영화 장르를 불러오는 중입니다."
    ):
        boxoffice_df = load_daily_boxoffice(
            KOBIS_KEY,
            target_dt,
        )

        if boxoffice_df.empty:
            st.warning(
                "조회한 날짜의 박스오피스 자료가 없습니다."
            )
            st.stop()

        df = add_genres_to_boxoffice(
            boxoffice_df,
            KOBIS_KEY,
        )

except RuntimeError as error:
    st.error(str(error))
    st.stop()


# ------------------------------------------------------------
# 11. 1위 영화 지표 카드
# ------------------------------------------------------------

top_movie = (
    df.sort_values("rank")
    .iloc[0]
)

column1, column2, column3 = st.columns(3)

with column1:
    render_top_movie_card(
        top_movie["movieNm"]
    )

with column2:
    st.metric(
        "어제 관객수",
        f"{int(top_movie['audiCnt']):,}명",
    )

with column3:
    st.metric(
        "누적 관객",
        f"{int(top_movie['audiAcc']):,}명",
    )


# ------------------------------------------------------------
# 12. 표에 사용할 자료 정리
# ------------------------------------------------------------

table = df[
    [
        "rank",
        "movieNm",
        "genres" if "genres" in df.columns else "movieCd",
    ]
].copy()

# 위에서 만든 임시 표를 실제 표시 열로 다시 구성합니다.
table = df[
    [
        "rank",
        "movieNm",
        "장르",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "showCnt",
    ]
].copy()

table.columns = [
    "전체 순위",
    "영화명",
    "장르",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수",
    "상영횟수",
]

table = (
    table.sort_values("전체 순위")
    .reset_index(drop=True)
)

integer_columns = [
    "전체 순위",
    "관객수",
    "누적관객",
    "스크린수",
    "상영횟수",
]

for column in integer_columns:
    table[column] = (
        pd.to_numeric(
            table[column],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )


# ------------------------------------------------------------
# 13. 전체 순위와 장르별 순위
# ------------------------------------------------------------

st.divider()

overall_tab, genre_tab, age_tab = st.tabs(
    [
        "📋 전체 순위",
        "🎭 장르별 순위",
        "👥 연령대별 인기",
    ]
)


with overall_tab:
    st.subheader("박스오피스 TOP 10")

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "전체 순위": st.column_config.NumberColumn(
                "순위",
                format="%d위",
                width="small",
            ),
            "영화명": st.column_config.TextColumn(
                "영화명",
                width="large",
            ),
            "장르": st.column_config.TextColumn(
                "장르",
                width="medium",
            ),
            "관객수": st.column_config.NumberColumn(
                "어제 관객수",
                format="%d명",
            ),
            "누적관객": st.column_config.NumberColumn(
                "누적 관객",
                format="%d명",
            ),
            "스크린수": st.column_config.NumberColumn(
                "스크린 수",
                format="%d개",
            ),
            "상영횟수": st.column_config.NumberColumn(
                "상영 횟수",
                format="%d회",
            ),
        },
    )

    st.subheader("관객수 상위 5편")

    top5 = (
        table.sort_values(
            "관객수",
            ascending=False,
        )
        .head(5)
    )

    st.bar_chart(
        top5.set_index("영화명")["관객수"],
        use_container_width=True,
    )


with genre_tab:
    st.subheader("장르별 박스오피스 순위")

    # 한 영화에 여러 장르가 들어 있을 수 있으므로
    # 쉼표를 기준으로 각각의 장르를 분리합니다.
    genre_table = table.copy()

    genre_table["장르 목록"] = (
        genre_table["장르"]
        .fillna("장르 정보 없음")
        .str.split(",")
    )

    genre_table = genre_table.explode(
        "장르 목록"
    )

    genre_table["장르 목록"] = (
        genre_table["장르 목록"]
        .astype(str)
        .str.strip()
    )

    available_genres = sorted(
        genre_table.loc[
            genre_table["장르 목록"]
            != "장르 정보 없음",
            "장르 목록",
        ]
        .dropna()
        .unique()
        .tolist()
    )

    if not available_genres:
        st.warning(
            "현재 박스오피스 영화의 장르 정보를 "
            "불러오지 못했습니다."
        )

    else:
        selected_genre = st.selectbox(
            "확인할 장르를 선택하세요.",
            options=available_genres,
        )

        selected_table = genre_table[
            genre_table["장르 목록"]
            == selected_genre
        ].copy()

        selected_table = (
            selected_table.sort_values(
                [
                    "관객수",
                    "전체 순위",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(drop=True)
        )

        # 선택한 장르 안에서 순위를 다시 매깁니다.
        selected_table.insert(
            0,
            "장르 순위",
            range(
                1,
                len(selected_table) + 1,
            ),
        )

        selected_table = selected_table[
            [
                "장르 순위",
                "전체 순위",
                "영화명",
                "장르",
                "관객수",
                "누적관객",
                "스크린수",
            ]
        ]

        st.dataframe(
            selected_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "장르 순위": st.column_config.NumberColumn(
                    f"{selected_genre} 순위",
                    format="%d위",
                ),
                "전체 순위": st.column_config.NumberColumn(
                    "전체 순위",
                    format="%d위",
                ),
                "관객수": st.column_config.NumberColumn(
                    "어제 관객수",
                    format="%d명",
                ),
                "누적관객": st.column_config.NumberColumn(
                    "누적 관객",
                    format="%d명",
                ),
                "스크린수": st.column_config.NumberColumn(
                    "스크린 수",
                    format="%d개",
                ),
            },
        )

        if len(selected_table) == 1:
            st.caption(
                f"어제 전체 TOP 10에는 "
                f"{selected_genre} 장르 영화가 1편 포함됐습니다."
            )
        else:
            st.caption(
                f"어제 전체 TOP 10에는 "
                f"{selected_genre} 장르 영화가 "
                f"{len(selected_table)}편 포함됐습니다."
            )

    st.info(
        "이 순위는 어제의 전체 박스오피스 TOP 10에 포함된 "
        "영화만 장르별로 다시 정렬한 결과입니다. "
        "전국에서 상영된 모든 영화를 대상으로 한 "
        "완전한 장르별 순위는 아닙니다."
    )


with age_tab:
    st.subheader("연령대별 인기 영화")

    st.warning(
        "KOBIS 공개 API에는 영화별 관객 연령대 자료가 없어 "
        "정확한 연령대별 인기 순위를 계산할 수 없습니다."
    )

    st.markdown(
        """
        연령대별 기능을 정확히 만들려면 다음 중 하나가 필요합니다.

        - 영화별 연령대 관객 비율을 제공하는 별도 데이터
        - 영화관이나 예매 서비스에서 제공하는 공식 분석 API
        - 직접 수집한 설문 또는 사용자 선호 데이터

        현재 앱에서는 임의로 연령대를 추정하지 않습니다.
        """
    )


# ------------------------------------------------------------
# 14. 자료 출처 안내
# ------------------------------------------------------------

st.divider()

st.caption(
    "자료 출처: 영화진흥위원회 영화관입장권통합전산망 "
    "KOBIS Open API"
)
