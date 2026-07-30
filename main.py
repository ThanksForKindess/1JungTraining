좌측 상단 글자 색 어디서 수정해? 코드 몇번째 줄이고 변경하는법 설명해줘

형님, 이번 오류는 코드 내용 문제가 아니라 들여쓰기 문제다.

기존 화면 출력 코드 전체가 아래처럼 try: 안에 들어가 있는데,

try:
    with st.spinner(...):
        ...

새로 추가한 st.markdown()이 왼쪽 끝에서 시작해 버려서 파이썬이 이렇게 판단한 기다.

“try 구역이 끝났네? 그러면 바로 except나 finally가 와야 하는데 왜 st.markdown이 나오노?”

수정 방법

855줄의 다음 코드부터:

st.markdown(

애니메이션 코드 마지막인:

st.caption(
    "색이 진한 붉은색으로 변할수록 현재보다 "
    "인구가 크게 감소한 지역입니다."
)

까지 전체를 스페이스 4칸 들여쓰기하면 된다.

즉 이렇게 되어야 한다.

    st.plotly_chart(
        map_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )

    # ------------------------------------------------------------
    # 향후 50년 인구 변화 애니메이션
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:10px;
            margin-bottom:10px;
            font-size:18px;
            font-weight:600;
        ">
            지금의 인구 변화가 계속된다면, 50년 뒤 우리 지역은 어떻게 변할까요?
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "show_population_animation" not in st.session_state:
        st.session_state["show_population_animation"] = False

    button_left, button_center, button_right = st.columns([1, 2, 1])

    with button_center:
        if st.button(
            "⚠ 향후 50년 인구 소멸 시뮬레이션 보기",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["show_population_animation"] = True

    if st.session_state["show_population_animation"]:
        st.warning(
            "이 지도는 공식 장래인구추계가 아닙니다. "
            "과거 인구 증감 추세가 앞으로도 계속된다고 가정한 "
            "시각적 시뮬레이션입니다."
        )

        with st.spinner(
            "향후 50년의 인구 변화 장면을 계산하고 있습니다."
        ):
            projection_df, projection_start_year, projection_end_year = (
                prepare_population_projection(
                    population_df=population_df,
                    geojson=geojson,
                    years_ahead=50,
                )
            )

            population_animation = (
                create_population_extinction_animation(
                    projection_df=projection_df,
                    geojson=geojson,
                )
            )

        st.subheader(
            f"{projection_start_year}년부터 "
            f"{projection_end_year}년까지의 인구 변화"
        )

        st.plotly_chart(
            population_animation,
            use_container_width=True,
            config={
                "displaylogo": False,
                "scrollZoom": False,
            },
        )

        st.caption(
            "색이 진한 붉은색으로 변할수록 현재보다 "
            "인구가 크게 감소한 지역입니다."
        )

    st.divider()

맨 앞을 보면 전부 이렇게 4칸 들어가 있어야 한다.

    st.markdown(

이렇게 왼쪽 끝이면 안 된다.

st.markdown(

그리고 파일 맨 아래 구조는 반드시 이런 순서를 유지해야 한다.

try:
    # 데이터 불러오기
    # 기존 지도
    # 새 애니메이션
    # 순위 표

except requests.RequestException as error:
    st.error(...)

except Exception as error:
    st.error(...)

가장 쉬운 수정법은 GitHub 편집기에서 새로 넣은 애니메이션 코드 전체를 드래그하고 Tab을 한 번 누르는 기다. 다만 Tab이 4칸보다 더 들어가면 안 되니, 각 최상위 줄이 기존 st.plotly_chart()와 세로로 똑같이 맞는지만 보면 된다.

ㅋㅋㅋ 스트림릿에서 튕겼다.. 코드 검사해줘

여기 깃허브 링크야

main.py
1m 13s 동안 처리함

ㅋㅋ 형님, 깃허브의 현재 main.py 전체를 문법 검사해보니 SyntaxError는 없다. 이번에는 코드 문법이 아니라 메모리 과부하로 스트림릿 서버가 죽은 가능성이 제일 크다.

현재 앱은 처음부터 남·여·계 나이 열을 전부 읽고, 애니메이션 버튼을 누르면 전체 데이터프레임을 또 복사한 다음 모든 계_ 열을 다시 숫자로 바꾼다. 이후 51개 연도의 지도 프레임까지 한꺼번에 만든다.

1. load_population_data()를 통째로 교체

현재 54줄 전후의 이 함수:

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_population_data(url: str) -> pd.DataFrame:

부터 함수 끝까지 지우고 아래로 교체해라.

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_population_data(url: str) -> pd.DataFrame:
    """
    인구 데이터를 내려받습니다.

    지도 계산에는 남성·여성별 열이 필요하지 않으므로
    '계_'로 시작하는 전체 인구 열만 읽어 메모리 사용량을 줄입니다.
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    file_bytes = response.content

    # 먼저 열 이름만 읽습니다.
    header_df = pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        nrows=0,
    )

    basic_columns = [
        "연도",
        "시도",
        "시군구",
        "동",
        "코드",
    ]

    # 남_·여_ 열은 제외하고 계_ 열만 가져옵니다.
    total_columns = [
        column
        for column in header_df.columns
        if str(column).startswith("계_")
    ]

    use_columns = basic_columns + total_columns

    return pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        usecols=use_columns,
        dtype={
            "코드": "string",
            "시도": "string",
            "시군구": "string",
            "동": "string",
        },
        low_memory=False,
    )

이 변경이 가장 중요하다. 기존에는 연령마다 계_, 남_, 여_를 다 읽었는데, 계산에 필요한 계_만 읽으므로 메모리가 대략 크게 줄어든다.

2. 미래예측 함수의 전체 복사를 제거

현재 356줄 전후에 있다.

df = population_df.copy()

이 한 줄을 지워라.

그리고 바로 아래의:

# 연도와 행정동 코드를 정리합니다.
df["연도"] = pd.to_numeric(df["연도"], errors="coerce")

부분까지 포함해서 아래처럼 바꿔라.

# 전체 인구 계산에 사용할 나이별 열을 찾습니다.
total_columns, _ = find_population_columns(population_df)

# 미래 시뮬레이션에 필요한 열만 골라 복사합니다.
# 시도·시군구·동 및 남녀별 자료는 여기서 필요하지 않습니다.
required_columns = [
    "연도",
    "코드",
] + total_columns

df = population_df.loc[:, required_columns].copy()

# 연도와 행정동 코드를 정리합니다.
df["연도"] = pd.to_numeric(
    df["연도"],
    errors="coerce",
)

df["코드"] = (
    df["코드"]
    .astype("string")
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(10)
)

df = df.dropna(subset=["연도", "코드"])
df["연도"] = df["연도"].astype(int)

# 행정동 코드 앞 5자리가 시군구 코드입니다.
df["시군구코드"] = df["코드"].str[:5]

그 아래쪽에 이미 있는 다음 줄은 중복되므로 삭제해야 한다.

total_columns, _ = find_population_columns(df)

최종적으로 이 부분이 두 번 있으면 안 된다.

3. 시뮬레이션 계산 결과 캐시

현재 344줄 전후의 함수 바로 위에 캐시를 추가해라.

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_population_projection(
    population_df: pd.DataFrame,
    geojson: dict,
    years_ahead: int = 50,
) -> tuple[pd.DataFrame, int, int]:

즉, 기존 함수에 위의 @st.cache_data(...) 한 줄만 붙이면 된다.

버튼 클릭이나 화면 조작으로 스트림릿이 다시 실행될 때 매번 50년치를 재계산하는 것을 막아준다.

4. 애니메이션 지도 생성도 캐시

현재 550줄 전후에서 다음 함수를 찾아라.

def create_population_extinction_animation(

바로 위에 이것을 붙여라.

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def create_population_extinction_animation(
    projection_df: pd.DataFrame,
    geojson: dict,
):
5. 버튼 중복 클릭 방지

현재 버튼 코드는 이미 애니메이션을 띄운 뒤에도 계속 같은 문구로 보인다. 아래처럼 바꾸면 낫다.

현재 816줄 전후:

with button_center:
    if st.button(
        "⚠ 향후 50년 인구 소멸 시뮬레이션 보기",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["show_population_animation"] = True

교체:

with button_center:
    button_label = (
        "▲ 인구 소멸 시뮬레이션 닫기"
        if st.session_state["show_population_animation"]
        else "⚠ 향후 50년 인구 소멸 시뮬레이션 보기"
    )

    if st.button(
        button_label,
        use_container_width=True,
        type="primary",
    ):
        st.session_state["show_population_animation"] = (
            not st.session_state["show_population_animation"]
        )
        st.rerun()
결론

현재 깃허브 파일은 들여쓰기와 문법은 정상이다. 기존 지도까지는 돌아가다가 애니메이션 버튼을 누르는 순간 앱이 통째로 튕겼다면, 거의 이 흐름이다.

전체 CSV 메모리 적재
→ 전체 데이터프레임 추가 복사
→ 100개 이상 나이 열 숫자 변환
→ 51년 × 255개 지역 지도 프레임 생성
→ Streamlit Cloud 메모리 한도 초과

위에서 1번과 2번은 반드시 적용, 3·4번도 같이 적용하는 게 좋다. 수정 후 커밋하고 Streamlit Cloud에서 Reboot app을 한 번 눌러야 기존 캐시와 죽은 프로세스가 깔끔하게 초기화된다.

그냥 수정한 코드 전체를 줘
2m 47s 동안 처리함

형님, 현재 깃허브 main.py 구조를 기준으로 메모리 절약 + 문법 오류 수정 + 애니메이션까지 포함한 전체 파일로 다시 정리했다. 파이썬 문법 검사도 통과시켰다. 현재 저장소 파일은 CSV 전체 열을 읽고 미래 계산에서 전체 데이터프레임을 다시 복사하는 구조라, 애니메이션 실행 시 메모리 부담이 커질 수 있었다.

아래 파일을 받아서 기존 main.py를 통째로 교체하면 된다.

main.py

추가 패키지는 없다. 기존 requirements.txt의 plotly, requests면 된다.

수정한 핵심은 이거다.

남_, 여_ 열은 아예 읽지 않고 계_ 열만 불러옴
65세이상인구 집계 문법 오류 제거
애니메이션 계산 때 필요한 열만 복사
나이별 계산이 끝나면 큰 데이터프레임을 바로 제거
데이터 계산 결과 캐시 적용
버튼으로 시뮬레이션 열기·닫기
현재 연도: 2026 → 2076 애니메이션 유지
try-except 내부 들여쓰기 전체 정리
범례 글자색 검은색 고정

GitHub에서 기존 내용을 전부 지우고 이 파일 내용을 붙여 넣은 다음 Commit changes하고, Streamlit Cloud에서 Reboot app 한 번 해주면 된다.

main.py
코드

라이브러리
/
main.py
# main.py
# ------------------------------------------------------------
# 전국 시군구별 고령화 지도 + 향후 50년 인구 변화 시뮬레이션
# ------------------------------------------------------------

import io
import re

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ------------------------------------------------------------
# 1. 기본 설정
# ------------------------------------------------------------

st.set_page_config(
    page_title="전국 고령화 지도",
    page_icon="🗺️",
    layout="wide",
)

POPULATION_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/population_yearly.csv.gz"
)

GEOJSON_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/boundaries/sigungu_kr.geojson"
)

AGE_GROUP_ORDER = [
    "19% 미만",
    "19% 이상 23% 미만",
    "23% 이상 28% 미만",
    "28% 이상 38% 미만",
    "38% 이상",
]

COLOR_MAP = {
    "19% 미만": "#fff7bc",
    "19% 이상 23% 미만": "#fee391",
    "23% 이상 28% 미만": "#fec44f",
    "28% 이상 38% 미만": "#fe9929",
    "38% 이상": "#cc4c02",
}

PROJECTION_ORDER = [
    "현재의 90% 이상",
    "현재의 75~90%",
    "현재의 50~75%",
    "현재의 25~50%",
    "현재의 25% 미만",
]

PROJECTION_COLORS = {
    "현재의 90% 이상": "#f2f2f2",
    "현재의 75~90%": "#fdd49e",
    "현재의 50~75%": "#fc8d59",
    "현재의 25~50%": "#d7301f",
    "현재의 25% 미만": "#67000d",
}


# ------------------------------------------------------------
# 2. 데이터 불러오기
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_population_data(url: str) -> pd.DataFrame:
    """
    인구 CSV를 내려받습니다.

    메모리 절약을 위해 계산에 필요한 기본 열과 '계_' 인구 열만 읽습니다.
    '코드'는 숫자가 아니라 지역 식별자이므로 문자열로 읽습니다.
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    file_bytes = response.content

    header_df = pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        nrows=0,
    )

    basic_columns = ["연도", "시도", "시군구", "동", "코드"]
    total_columns = [
        column
        for column in header_df.columns
        if str(column).startswith("계_")
    ]

    missing = [
        column for column in basic_columns
        if column not in header_df.columns
    ]
    if missing:
        raise ValueError(
            "인구 데이터에 필요한 열이 없습니다: " + ", ".join(missing)
        )

    if not total_columns:
        raise ValueError("'계_'로 시작하는 나이별 인구 열을 찾지 못했습니다.")

    return pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        usecols=basic_columns + total_columns,
        dtype={
            "코드": "string",
            "시도": "string",
            "시군구": "string",
            "동": "string",
        },
        low_memory=False,
    )


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_geojson(url: str) -> dict:
    """전국 시군구 경계 GeoJSON을 내려받습니다."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.json()


# ------------------------------------------------------------
# 3. 공통 데이터 처리 함수
# ------------------------------------------------------------

def get_age_from_column(column_name: str):
    """
    '계_65세', '계_100세 이상' 열 이름에서 나이를 꺼냅니다.
    """
    if not column_name.startswith("계_"):
        return None

    match = re.fullmatch(r"계_(\d+)세(?: 이상)?", column_name)
    if match is None:
        return None

    return int(match.group(1))


def find_population_columns(df: pd.DataFrame):
    """전체 인구 열과 65세 이상 인구 열을 찾습니다."""
    total_columns = []
    senior_columns = []

    for column in df.columns:
        age = get_age_from_column(str(column))
        if age is None:
            continue

        total_columns.append(column)
        if age >= 65:
            senior_columns.append(column)

    if not total_columns:
        raise ValueError("나이별 전체 인구 열을 찾지 못했습니다.")
    if not senior_columns:
        raise ValueError("65세 이상 인구 열을 찾지 못했습니다.")

    return total_columns, senior_columns


def clean_code(series: pd.Series, length: int) -> pd.Series:
    """행정구역 코드를 지정한 길이의 문자열로 정리합니다."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(length)
    )


def convert_population_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """쉼표가 포함된 인구 값을 숫자로 변환합니다."""
    for column in columns:
        df[column] = pd.to_numeric(
            df[column]
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce",
        ).fillna(0)

    return df


def make_region_table(geojson: dict) -> pd.DataFrame:
    """GeoJSON의 코드·시도·시군구 속성을 표로 만듭니다."""
    rows = []

    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("코드", "")).strip().zfill(5)

        feature.setdefault("properties", {})["코드"] = code

        rows.append(
            {
                "코드": code,
                "시도": properties.get("시도", ""),
                "시군구": properties.get("시군구", ""),
            }
        )

    region_df = pd.DataFrame(rows)
    if region_df.empty:
        raise ValueError("GeoJSON에서 시군구 정보를 찾지 못했습니다.")

    return region_df


# ------------------------------------------------------------
# 4. 최신 연도 고령화율 계산
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_aging_data(
    population_df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """최신 연도의 시군구별 고령화율을 계산합니다."""
    total_columns, senior_columns = find_population_columns(population_df)

    working_columns = ["연도", "코드"] + total_columns
    df = population_df.loc[:, working_columns].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])
    if df.empty:
        raise ValueError("사용할 수 있는 연도 데이터가 없습니다.")

    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    df["코드"] = clean_code(df["코드"], 10)
    df["시군구코드"] = df["코드"].str[:5]

    df = convert_population_columns(df, total_columns)
    df["전체인구"] = df[total_columns].sum(axis=1)
    df["65세이상인구"] = df[senior_columns].sum(axis=1)

    sigungu_df = (
        df.groupby("시군구코드", as_index=False)[
            ["전체인구", "65세이상인구"]
        ]
        .sum()
    )

    sigungu_df["고령화율"] = np.where(
        sigungu_df["전체인구"] > 0,
        sigungu_df["65세이상인구"] / sigungu_df["전체인구"] * 100,
        np.nan,
    )

    return sigungu_df, latest_year


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_map_data(
    geojson: dict,
    aging_df: pd.DataFrame,
) -> pd.DataFrame:
    """GeoJSON 지역 정보와 고령화율을 코드 기준으로 연결합니다."""
    region_df = make_region_table(geojson)

    map_df = region_df.merge(
        aging_df,
        how="left",
        left_on="코드",
        right_on="시군구코드",
    )

    map_df["고령화 단계"] = pd.cut(
        map_df["고령화율"],
        bins=[-np.inf, 19, 23, 28, 38, np.inf],
        labels=AGE_GROUP_ORDER,
        right=False,
    )

    map_df["고령화율 표시"] = map_df["고령화율"].round(1)
    map_df["전체인구 표시"] = map_df["전체인구"].round().astype("Int64")
    map_df["65세이상인구 표시"] = (
        map_df["65세이상인구"].round().astype("Int64")
    )

    return map_df


# ------------------------------------------------------------
# 5. 현재 고령화 지도 만들기
# ------------------------------------------------------------

def create_choropleth(map_df: pd.DataFrame, geojson: dict):
    """배경 타일 없이 시군구 경계만 보이는 단계구분도를 만듭니다."""
    drawable_df = map_df.dropna(
        subset=["고령화율", "고령화 단계"]
    ).copy()

    fig = px.choropleth(
        drawable_df,
        geojson=geojson,
        locations="코드",
        featureidkey="properties.코드",
        color="고령화 단계",
        category_orders={"고령화 단계": AGE_GROUP_ORDER},
        color_discrete_map=COLOR_MAP,
        custom_data=["시군구", "시도", "고령화율 표시"],
    )

    fig.update_traces(
        marker_line_color="#666666",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "시도: %{customdata[1]}<br>"
            "고령화율: %{customdata[2]:.1f}%"
            "<extra></extra>"
        ),
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showcountries=False,
        showland=False,
        showlakes=False,
        showocean=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            title="65세 이상 인구 비율",
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#cccccc",
            borderwidth=1,
            traceorder="normal",
            font=dict(color="#000000", size=13),
            title_font=dict(color="#000000", size=14),
        ),
    )

    return fig


# ------------------------------------------------------------
# 6. 향후 50년 인구 변화 시뮬레이션
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_population_projection(
    population_df: pd.DataFrame,
    geojson: dict,
    years_ahead: int = 50,
) -> tuple[pd.DataFrame, int, int]:
    """
    2015년부터 최신 연도까지의 시군구별 인구 변화율이
    앞으로도 이어진다고 가정하여 향후 인구를 단순 계산합니다.

    공식 장래인구추계가 아닌 시각적 시뮬레이션입니다.
    """
    total_columns, _ = find_population_columns(population_df)

    # 필요한 열만 복사해 메모리 사용량을 줄입니다.
    df = population_df.loc[:, ["연도", "코드"] + total_columns].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["코드"] = clean_code(df["코드"], 10)
    df = df.dropna(subset=["연도", "코드"])
    df["연도"] = df["연도"].astype(int)
    df["시군구코드"] = df["코드"].str[:5]

    df = convert_population_columns(df, total_columns)
    df["전체인구"] = df[total_columns].sum(axis=1)

    # 나이별 열은 더 이상 필요 없으므로 즉시 제거합니다.
    compact_df = df[["연도", "시군구코드", "전체인구"]].copy()
    del df

    yearly_population = (
        compact_df.groupby(
            ["연도", "시군구코드"],
            as_index=False,
        )["전체인구"]
        .sum()
    )

    first_year = int(yearly_population["연도"].min())
    latest_year = int(yearly_population["연도"].max())
    year_count = max(latest_year - first_year, 1)

    first_population = (
        yearly_population[
            yearly_population["연도"] == first_year
        ][["시군구코드", "전체인구"]]
        .rename(columns={"전체인구": "최초인구"})
    )

    latest_population = (
        yearly_population[
            yearly_population["연도"] == latest_year
        ][["시군구코드", "전체인구"]]
        .rename(columns={"전체인구": "현재인구"})
    )

    trend_df = latest_population.merge(
        first_population,
        on="시군구코드",
        how="left",
    )

    valid_mask = (
        trend_df["최초인구"].notna()
        & (trend_df["최초인구"] > 0)
        & (trend_df["현재인구"] > 0)
    )

    trend_df["연평균변화율"] = 0.0
    trend_df.loc[valid_mask, "연평균변화율"] = (
        (
            trend_df.loc[valid_mask, "현재인구"]
            / trend_df.loc[valid_mask, "최초인구"]
        )
        ** (1 / year_count)
        - 1
    )

    # 지나치게 큰 변화가 장기 예측을 왜곡하지 않도록 범위를 제한합니다.
    trend_df["연평균변화율"] = trend_df[
        "연평균변화율"
    ].clip(lower=-0.08, upper=0.02)

    region_df = make_region_table(geojson).rename(
        columns={"코드": "시군구코드"}
    )

    trend_df = region_df.merge(
        trend_df,
        on="시군구코드",
        how="left",
    )

    trend_df["연평균변화율"] = trend_df[
        "연평균변화율"
    ].fillna(0)

    frames = []

    # 0년부터 50년 뒤까지 51개 장면을 만듭니다.
    for elapsed_year in range(years_ahead + 1):
        frame = trend_df.copy()
        frame["연도"] = latest_year + elapsed_year

        frame["예상인구"] = (
            frame["현재인구"]
            * (1 + frame["연평균변화율"]) ** elapsed_year
        )

        frame["현재대비인구"] = np.where(
            frame["현재인구"] > 0,
            frame["예상인구"] / frame["현재인구"] * 100,
            np.nan,
        )

        frames.append(
            frame[
                [
                    "시군구코드",
                    "시도",
                    "시군구",
                    "연도",
                    "현재인구",
                    "예상인구",
                    "현재대비인구",
                    "연평균변화율",
                ]
            ]
        )

    projection_df = pd.concat(frames, ignore_index=True)

    projection_df["인구 변화 단계"] = pd.cut(
        projection_df["현재대비인구"],
        bins=[-np.inf, 25, 50, 75, 90, np.inf],
        labels=[
            "현재의 25% 미만",
            "현재의 25~50%",
            "현재의 50~75%",
            "현재의 75~90%",
            "현재의 90% 이상",
        ],
        right=False,
    )

    projection_df["인구 변화 단계"] = pd.Categorical(
        projection_df["인구 변화 단계"],
        categories=PROJECTION_ORDER,
        ordered=True,
    )

    projection_df["현재인구 표시"] = (
        projection_df["현재인구"].round().astype("Int64")
    )
    projection_df["예상인구 표시"] = (
        projection_df["예상인구"].round().astype("Int64")
    )
    projection_df["현재대비인구 표시"] = (
        projection_df["현재대비인구"].round(1)
    )
    projection_df["연평균변화율 표시"] = (
        projection_df["연평균변화율"] * 100
    ).round(2)

    return projection_df, latest_year, latest_year + years_ahead


def create_population_extinction_animation(
    projection_df: pd.DataFrame,
    geojson: dict,
):
    """향후 50년 인구 변화 애니메이션 지도를 만듭니다."""
    drawable_df = projection_df.dropna(
        subset=["현재대비인구", "인구 변화 단계"]
    ).copy()

    fig = px.choropleth(
        drawable_df,
        geojson=geojson,
        locations="시군구코드",
        featureidkey="properties.코드",
        color="인구 변화 단계",
        animation_frame="연도",
        category_orders={"인구 변화 단계": PROJECTION_ORDER},
        color_discrete_map=PROJECTION_COLORS,
        custom_data=[
            "시군구",
            "시도",
            "현재인구 표시",
            "예상인구 표시",
            "현재대비인구 표시",
            "연평균변화율 표시",
        ],
    )

    fig.update_traces(
        marker_line_color="#555555",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "시도: %{customdata[1]}<br>"
            "현재 인구: %{customdata[2]:,}명<br>"
            "시뮬레이션 인구: %{customdata[3]:,}명<br>"
            "현재 대비: %{customdata[4]:.1f}%<br>"
            "과거 연평균 변화율: %{customdata[5]:.2f}%"
            "<extra></extra>"
        ),
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showcountries=False,
        showland=False,
        showlakes=False,
        showocean=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=780,
        margin=dict(l=0, r=0, t=20, b=100),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            title="현재 인구 대비 잔존 비율",
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#999999",
            borderwidth=1,
            font=dict(color="#111111", size=13),
            title_font=dict(color="#111111", size=14),
        ),
    )

    if fig.layout.sliders:
        slider = fig.layout.sliders[0]
        slider.currentvalue = {
            "prefix": "현재 연도: ",
            "font": {"size": 28, "color": "#67000d"},
            "visible": True,
            "xanchor": "center",
        }
        slider.x = 0.12
        slider.len = 0.76
        slider.pad = {"t": 45, "b": 10}

    if fig.layout.updatemenus:
        play_button = fig.layout.updatemenus[0].buttons[0]
        play_button.args[1]["frame"]["duration"] = 260
        play_button.args[1]["transition"]["duration"] = 120
        play_button.label = "▶ 50년 재생"

    return fig


# ------------------------------------------------------------
# 7. 순위 표
# ------------------------------------------------------------

def make_ranking_table(
    map_df: pd.DataFrame,
    ascending: bool,
) -> pd.DataFrame:
    """고령화율 상위 또는 하위 10개 지역 표를 만듭니다."""
    ranking_df = (
        map_df.dropna(subset=["고령화율"])
        .sort_values(
            by=["고령화율", "시도", "시군구"],
            ascending=[ascending, True, True],
        )
        .head(10)
        .copy()
    )

    ranking_df.insert(0, "순위", range(1, len(ranking_df) + 1))
    ranking_df["지역"] = (
        ranking_df["시도"].astype(str)
        + " "
        + ranking_df["시군구"].astype(str)
    )
    ranking_df["고령화율(%)"] = ranking_df["고령화율"].round(1)
    ranking_df["전체 인구"] = ranking_df["전체인구"].round().astype("Int64")
    ranking_df["65세 이상"] = (
        ranking_df["65세이상인구"].round().astype("Int64")
    )

    return ranking_df[
        ["순위", "지역", "고령화율(%)", "전체 인구", "65세 이상"]
    ]


# ------------------------------------------------------------
# 8. 앱 화면
# ------------------------------------------------------------

st.title("🗺️ 전국 시군구별 고령화 지도")
st.caption("시군구별 전체 인구에서 65세 이상 인구가 차지하는 비율")

try:
    with st.spinner("전국 인구와 지도 경계 데이터를 불러오는 중입니다."):
        population_df = load_population_data(POPULATION_URL)
        geojson = load_geojson(GEOJSON_URL)
        aging_df, latest_year = prepare_aging_data(population_df)
        map_df = prepare_map_data(geojson, aging_df)

    matched_count = int(map_df["고령화율"].notna().sum())
    total_region_count = len(map_df)
    national_population = map_df["전체인구"].sum()
    national_senior_population = map_df["65세이상인구"].sum()

    national_aging_rate = (
        national_senior_population / national_population * 100
        if national_population > 0
        else np.nan
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("기준 연도", f"{latest_year}년")
    metric_col2.metric(
        "전국 고령화율",
        f"{national_aging_rate:.1f}%"
        if pd.notna(national_aging_rate)
        else "-",
    )
    metric_col3.metric(
        "지도 연결 지역",
        f"{matched_count} / {total_region_count}개",
    )

    if matched_count < total_region_count:
        missing_regions = map_df.loc[
            map_df["고령화율"].isna(),
            ["시도", "시군구", "코드"],
        ]

        with st.expander(
            f"인구 데이터가 연결되지 않은 지역 "
            f"{total_region_count - matched_count}개 보기"
        ):
            st.dataframe(
                missing_regions,
                hide_index=True,
                use_container_width=True,
            )

    map_figure = create_choropleth(map_df, geojson)
    st.plotly_chart(
        map_figure,
        use_container_width=True,
        config={"displaylogo": False, "scrollZoom": False},
    )

    # --------------------------------------------------------
    # 향후 50년 시뮬레이션 버튼과 애니메이션
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:10px;
            margin-bottom:10px;
            font-size:18px;
            font-weight:600;
        ">
            지금의 인구 변화가 계속된다면, 50년 뒤 우리 지역은 어떻게 변할까요?
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "show_population_animation" not in st.session_state:
        st.session_state["show_population_animation"] = False

    button_left, button_center, button_right = st.columns([1, 2, 1])

    with button_center:
        button_label = (
            "▲ 인구 변화 시뮬레이션 닫기"
            if st.session_state["show_population_animation"]
            else "⚠ 향후 50년 인구 소멸 시뮬레이션 보기"
        )

        if st.button(
            button_label,
            use_container_width=True,
            type="primary",
        ):
            st.session_state["show_population_animation"] = (
                not st.session_state["show_population_animation"]
            )
            st.rerun()

    if st.session_state["show_population_animation"]:
        st.warning(
            "이 지도는 공식 장래인구추계가 아닙니다. "
            "2015년부터 최신 연도까지의 인구 증감 추세가 "
            "앞으로도 계속된다고 가정한 시각적 시뮬레이션입니다."
        )

        with st.spinner("향후 50년의 인구 변화 장면을 계산하고 있습니다."):
            projection_df, projection_start_year, projection_end_year = (
                prepare_population_projection(
                    population_df=population_df,
                    geojson=geojson,
                    years_ahead=50,
                )
            )
            population_animation = create_population_extinction_animation(
                projection_df=projection_df,
                geojson=geojson,
            )

        st.subheader(
            f"{projection_start_year}년부터 "
            f"{projection_end_year}년까지의 인구 변화"
        )

        st.plotly_chart(
            population_animation,
            use_container_width=True,
            config={"displaylogo": False, "scrollZoom": False},
        )

        st.caption(
            "색이 진한 붉은색으로 변할수록 현재보다 인구가 크게 감소한 지역입니다."
        )

    st.divider()

    # --------------------------------------------------------
    # 고령화율 상위·하위 표
    # --------------------------------------------------------

    high_ranking = make_ranking_table(map_df, ascending=False)
    low_ranking = make_ranking_table(map_df, ascending=True)

    left_column, right_column = st.columns(2, gap="large")

    table_columns = {
        "순위": st.column_config.NumberColumn("순위", format="%d위"),
        "고령화율(%)": st.column_config.NumberColumn(
            "고령화율",
            format="%.1f%%",
        ),
        "전체 인구": st.column_config.NumberColumn(
            "전체 인구",
            format="%d명",
        ),
        "65세 이상": st.column_config.NumberColumn(
            "65세 이상",
            format="%d명",
        ),
    }

    with left_column:
        st.subheader("고령화율이 높은 지역 10곳")
        st.dataframe(
            high_ranking,
            hide_index=True,
            use_container_width=True,
            column_config=table_columns,
        )

    with right_column:
        st.subheader("고령화율이 낮은 지역 10곳")
        st.dataframe(
            low_ranking,
            hide_index=True,
            use_container_width=True,
            column_config=table_columns,
        )

    st.caption(
        "고령화율 = 시군구의 65세 이상 인구 ÷ 시군구 전체 인구 × 100"
    )

except requests.RequestException as error:
    st.error("인터넷에서 데이터를 내려받지 못했습니다.")
    st.exception(error)

except Exception as error:
    st.error("데이터를 처리하거나 지도를 만드는 중 오류가 발생했습니다.")
    st.exception(error)

라이브러리
/
main.py
# main.py
# ------------------------------------------------------------
# 전국 시군구별 고령화 지도 + 향후 50년 인구 변화 시뮬레이션
# ------------------------------------------------------------

import io
import re

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ------------------------------------------------------------
# 1. 기본 설정
# ------------------------------------------------------------

st.set_page_config(
    page_title="전국 고령화 지도",
    page_icon="🗺️",
    layout="wide",
)

POPULATION_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/population_yearly.csv.gz"
)

GEOJSON_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/boundaries/sigungu_kr.geojson"
)

AGE_GROUP_ORDER = [
    "19% 미만",
    "19% 이상 23% 미만",
    "23% 이상 28% 미만",
    "28% 이상 38% 미만",
    "38% 이상",
]

COLOR_MAP = {
    "19% 미만": "#fff7bc",
    "19% 이상 23% 미만": "#fee391",
    "23% 이상 28% 미만": "#fec44f",
    "28% 이상 38% 미만": "#fe9929",
    "38% 이상": "#cc4c02",
}

PROJECTION_ORDER = [
    "현재의 90% 이상",
    "현재의 75~90%",
    "현재의 50~75%",
    "현재의 25~50%",
    "현재의 25% 미만",
]

PROJECTION_COLORS = {
    "현재의 90% 이상": "#f2f2f2",
    "현재의 75~90%": "#fdd49e",
    "현재의 50~75%": "#fc8d59",
    "현재의 25~50%": "#d7301f",
    "현재의 25% 미만": "#67000d",
}


# ------------------------------------------------------------
# 2. 데이터 불러오기
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_population_data(url: str) -> pd.DataFrame:
    """
    인구 CSV를 내려받습니다.

    메모리 절약을 위해 계산에 필요한 기본 열과 '계_' 인구 열만 읽습니다.
    '코드'는 숫자가 아니라 지역 식별자이므로 문자열로 읽습니다.
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    file_bytes = response.content

    header_df = pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        nrows=0,
    )

    basic_columns = ["연도", "시도", "시군구", "동", "코드"]
    total_columns = [
        column
        for column in header_df.columns
        if str(column).startswith("계_")
    ]

    missing = [
        column for column in basic_columns
        if column not in header_df.columns
    ]
    if missing:
        raise ValueError(
            "인구 데이터에 필요한 열이 없습니다: " + ", ".join(missing)
        )

    if not total_columns:
        raise ValueError("'계_'로 시작하는 나이별 인구 열을 찾지 못했습니다.")

    return pd.read_csv(
        io.BytesIO(file_bytes),
        compression="gzip",
        usecols=basic_columns + total_columns,
        dtype={
            "코드": "string",
            "시도": "string",
            "시군구": "string",
            "동": "string",
        },
        low_memory=False,
    )


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_geojson(url: str) -> dict:
    """전국 시군구 경계 GeoJSON을 내려받습니다."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.json()


# ------------------------------------------------------------
# 3. 공통 데이터 처리 함수
# ------------------------------------------------------------

def get_age_from_column(column_name: str):
    """
    '계_65세', '계_100세 이상' 열 이름에서 나이를 꺼냅니다.
    """
    if not column_name.startswith("계_"):
        return None

    match = re.fullmatch(r"계_(\d+)세(?: 이상)?", column_name)
    if match is None:
        return None

    return int(match.group(1))


def find_population_columns(df: pd.DataFrame):
    """전체 인구 열과 65세 이상 인구 열을 찾습니다."""
    total_columns = []
    senior_columns = []

    for column in df.columns:
        age = get_age_from_column(str(column))
        if age is None:
            continue

        total_columns.append(column)
        if age >= 65:
            senior_columns.append(column)

    if not total_columns:
        raise ValueError("나이별 전체 인구 열을 찾지 못했습니다.")
    if not senior_columns:
        raise ValueError("65세 이상 인구 열을 찾지 못했습니다.")

    return total_columns, senior_columns


def clean_code(series: pd.Series, length: int) -> pd.Series:
    """행정구역 코드를 지정한 길이의 문자열로 정리합니다."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(length)
    )


def convert_population_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """쉼표가 포함된 인구 값을 숫자로 변환합니다."""
    for column in columns:
        df[column] = pd.to_numeric(
            df[column]
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce",
        ).fillna(0)

    return df


def make_region_table(geojson: dict) -> pd.DataFrame:
    """GeoJSON의 코드·시도·시군구 속성을 표로 만듭니다."""
    rows = []

    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("코드", "")).strip().zfill(5)

        feature.setdefault("properties", {})["코드"] = code

        rows.append(
            {
                "코드": code,
                "시도": properties.get("시도", ""),
                "시군구": properties.get("시군구", ""),
            }
        )

    region_df = pd.DataFrame(rows)
    if region_df.empty:
        raise ValueError("GeoJSON에서 시군구 정보를 찾지 못했습니다.")

    return region_df


# ------------------------------------------------------------
# 4. 최신 연도 고령화율 계산
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_aging_data(
    population_df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """최신 연도의 시군구별 고령화율을 계산합니다."""
    total_columns, senior_columns = find_population_columns(population_df)

    working_columns = ["연도", "코드"] + total_columns
    df = population_df.loc[:, working_columns].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])
    if df.empty:
        raise ValueError("사용할 수 있는 연도 데이터가 없습니다.")

    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    df["코드"] = clean_code(df["코드"], 10)
    df["시군구코드"] = df["코드"].str[:5]

    df = convert_population_columns(df, total_columns)
    df["전체인구"] = df[total_columns].sum(axis=1)
    df["65세이상인구"] = df[senior_columns].sum(axis=1)

    sigungu_df = (
        df.groupby("시군구코드", as_index=False)[
            ["전체인구", "65세이상인구"]
        ]
        .sum()
    )

    sigungu_df["고령화율"] = np.where(
        sigungu_df["전체인구"] > 0,
        sigungu_df["65세이상인구"] / sigungu_df["전체인구"] * 100,
        np.nan,
    )

    return sigungu_df, latest_year


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_map_data(
    geojson: dict,
    aging_df: pd.DataFrame,
) -> pd.DataFrame:
    """GeoJSON 지역 정보와 고령화율을 코드 기준으로 연결합니다."""
    region_df = make_region_table(geojson)

    map_df = region_df.merge(
        aging_df,
        how="left",
        left_on="코드",
        right_on="시군구코드",
    )

    map_df["고령화 단계"] = pd.cut(
        map_df["고령화율"],
        bins=[-np.inf, 19, 23, 28, 38, np.inf],
        labels=AGE_GROUP_ORDER,
        right=False,
    )

    map_df["고령화율 표시"] = map_df["고령화율"].round(1)
    map_df["전체인구 표시"] = map_df["전체인구"].round().astype("Int64")
    map_df["65세이상인구 표시"] = (
        map_df["65세이상인구"].round().astype("Int64")
    )

    return map_df


# ------------------------------------------------------------
# 5. 현재 고령화 지도 만들기
# ------------------------------------------------------------

def create_choropleth(map_df: pd.DataFrame, geojson: dict):
    """배경 타일 없이 시군구 경계만 보이는 단계구분도를 만듭니다."""
    drawable_df = map_df.dropna(
        subset=["고령화율", "고령화 단계"]
    ).copy()

    fig = px.choropleth(
        drawable_df,
        geojson=geojson,
        locations="코드",
        featureidkey="properties.코드",
        color="고령화 단계",
        category_orders={"고령화 단계": AGE_GROUP_ORDER},
        color_discrete_map=COLOR_MAP,
        custom_data=["시군구", "시도", "고령화율 표시"],
    )

    fig.update_traces(
        marker_line_color="#666666",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "시도: %{customdata[1]}<br>"
            "고령화율: %{customdata[2]:.1f}%"
            "<extra></extra>"
        ),
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showcountries=False,
        showland=False,
        showlakes=False,
        showocean=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            title="65세 이상 인구 비율",
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#cccccc",
            borderwidth=1,
            traceorder="normal",
            font=dict(color="#000000", size=13),
            title_font=dict(color="#000000", size=14),
        ),
    )

    return fig


# ------------------------------------------------------------
# 6. 향후 50년 인구 변화 시뮬레이션
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def prepare_population_projection(
    population_df: pd.DataFrame,
    geojson: dict,
    years_ahead: int = 50,
) -> tuple[pd.DataFrame, int, int]:
    """
    2015년부터 최신 연도까지의 시군구별 인구 변화율이
    앞으로도 이어진다고 가정하여 향후 인구를 단순 계산합니다.

    공식 장래인구추계가 아닌 시각적 시뮬레이션입니다.
    """
    total_columns, _ = find_population_columns(population_df)

    # 필요한 열만 복사해 메모리 사용량을 줄입니다.
    df = population_df.loc[:, ["연도", "코드"] + total_columns].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["코드"] = clean_code(df["코드"], 10)
    df = df.dropna(subset=["연도", "코드"])
    df["연도"] = df["연도"].astype(int)
    df["시군구코드"] = df["코드"].str[:5]

    df = convert_population_columns(df, total_columns)
    df["전체인구"] = df[total_columns].sum(axis=1)

    # 나이별 열은 더 이상 필요 없으므로 즉시 제거합니다.
    compact_df = df[["연도", "시군구코드", "전체인구"]].copy()
    del df

    yearly_population = (
        compact_df.groupby(
            ["연도", "시군구코드"],
            as_index=False,
        )["전체인구"]
        .sum()
    )

    first_year = int(yearly_population["연도"].min())
    latest_year = int(yearly_population["연도"].max())
    year_count = max(latest_year - first_year, 1)

    first_population = (
        yearly_population[
            yearly_population["연도"] == first_year
        ][["시군구코드", "전체인구"]]
        .rename(columns={"전체인구": "최초인구"})
    )

    latest_population = (
        yearly_population[
            yearly_population["연도"] == latest_year
        ][["시군구코드", "전체인구"]]
        .rename(columns={"전체인구": "현재인구"})
    )

    trend_df = latest_population.merge(
        first_population,
        on="시군구코드",
        how="left",
    )

    valid_mask = (
        trend_df["최초인구"].notna()
        & (trend_df["최초인구"] > 0)
        & (trend_df["현재인구"] > 0)
    )

    trend_df["연평균변화율"] = 0.0
    trend_df.loc[valid_mask, "연평균변화율"] = (
        (
            trend_df.loc[valid_mask, "현재인구"]
            / trend_df.loc[valid_mask, "최초인구"]
        )
        ** (1 / year_count)
        - 1
    )

    # 지나치게 큰 변화가 장기 예측을 왜곡하지 않도록 범위를 제한합니다.
    trend_df["연평균변화율"] = trend_df[
        "연평균변화율"
    ].clip(lower=-0.08, upper=0.02)

    region_df = make_region_table(geojson).rename(
        columns={"코드": "시군구코드"}
    )

    trend_df = region_df.merge(
        trend_df,
        on="시군구코드",
        how="left",
    )

    trend_df["연평균변화율"] = trend_df[
        "연평균변화율"
    ].fillna(0)

    frames = []

    # 0년부터 50년 뒤까지 51개 장면을 만듭니다.
    for elapsed_year in range(years_ahead + 1):
        frame = trend_df.copy()
        frame["연도"] = latest_year + elapsed_year

        frame["예상인구"] = (
            frame["현재인구"]
            * (1 + frame["연평균변화율"]) ** elapsed_year
        )

        frame["현재대비인구"] = np.where(
            frame["현재인구"] > 0,
            frame["예상인구"] / frame["현재인구"] * 100,
            np.nan,
        )

        frames.append(
            frame[
                [
                    "시군구코드",
                    "시도",
                    "시군구",
                    "연도",
                    "현재인구",
                    "예상인구",
                    "현재대비인구",
                    "연평균변화율",
                ]
            ]
        )

    projection_df = pd.concat(frames, ignore_index=True)

    projection_df["인구 변화 단계"] = pd.cut(
        projection_df["현재대비인구"],
        bins=[-np.inf, 25, 50, 75, 90, np.inf],
        labels=[
            "현재의 25% 미만",
            "현재의 25~50%",
            "현재의 50~75%",
            "현재의 75~90%",
            "현재의 90% 이상",
        ],
        right=False,
    )

    projection_df["인구 변화 단계"] = pd.Categorical(
        projection_df["인구 변화 단계"],
        categories=PROJECTION_ORDER,
        ordered=True,
    )

    projection_df["현재인구 표시"] = (
        projection_df["현재인구"].round().astype("Int64")
    )
    projection_df["예상인구 표시"] = (
        projection_df["예상인구"].round().astype("Int64")
    )
    projection_df["현재대비인구 표시"] = (
        projection_df["현재대비인구"].round(1)
    )
    projection_df["연평균변화율 표시"] = (
        projection_df["연평균변화율"] * 100
    ).round(2)

    return projection_df, latest_year, latest_year + years_ahead


def create_population_extinction_animation(
    projection_df: pd.DataFrame,
    geojson: dict,
):
    """향후 50년 인구 변화 애니메이션 지도를 만듭니다."""
    drawable_df = projection_df.dropna(
        subset=["현재대비인구", "인구 변화 단계"]
    ).copy()

    fig = px.choropleth(
        drawable_df,
        geojson=geojson,
        locations="시군구코드",
        featureidkey="properties.코드",
        color="인구 변화 단계",
        animation_frame="연도",
        category_orders={"인구 변화 단계": PROJECTION_ORDER},
        color_discrete_map=PROJECTION_COLORS,
        custom_data=[
            "시군구",
            "시도",
            "현재인구 표시",
            "예상인구 표시",
            "현재대비인구 표시",
            "연평균변화율 표시",
        ],
    )

    fig.update_traces(
        marker_line_color="#555555",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "시도: %{customdata[1]}<br>"
            "현재 인구: %{customdata[2]:,}명<br>"
            "시뮬레이션 인구: %{customdata[3]:,}명<br>"
            "현재 대비: %{customdata[4]:.1f}%<br>"
            "과거 연평균 변화율: %{customdata[5]:.2f}%"
            "<extra></extra>"
        ),
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showcountries=False,
        showland=False,
        showlakes=False,
        showocean=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=780,
        margin=dict(l=0, r=0, t=20, b=100),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            title="현재 인구 대비 잔존 비율",
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#999999",
            borderwidth=1,
            font=dict(color="#111111", size=13),
            title_font=dict(color="#111111", size=14),
        ),
    )

    if fig.layout.sliders:
        slider = fig.layout.sliders[0]
        slider.currentvalue = {
            "prefix": "현재 연도: ",
            "font": {"size": 28, "color": "#67000d"},
            "visible": True,
            "xanchor": "center",
        }
        slider.x = 0.12
        slider.len = 0.76
        slider.pad = {"t": 45, "b": 10}

    if fig.layout.updatemenus:
        play_button = fig.layout.updatemenus[0].buttons[0]
        play_button.args[1]["frame"]["duration"] = 260
        play_button.args[1]["transition"]["duration"] = 120
        play_button.label = "▶ 50년 재생"

    return fig


# ------------------------------------------------------------
# 7. 순위 표
# ------------------------------------------------------------

def make_ranking_table(
    map_df: pd.DataFrame,
    ascending: bool,
) -> pd.DataFrame:
    """고령화율 상위 또는 하위 10개 지역 표를 만듭니다."""
    ranking_df = (
        map_df.dropna(subset=["고령화율"])
        .sort_values(
            by=["고령화율", "시도", "시군구"],
            ascending=[ascending, True, True],
        )
        .head(10)
        .copy()
    )

    ranking_df.insert(0, "순위", range(1, len(ranking_df) + 1))
    ranking_df["지역"] = (
        ranking_df["시도"].astype(str)
        + " "
        + ranking_df["시군구"].astype(str)
    )
    ranking_df["고령화율(%)"] = ranking_df["고령화율"].round(1)
    ranking_df["전체 인구"] = ranking_df["전체인구"].round().astype("Int64")
    ranking_df["65세 이상"] = (
        ranking_df["65세이상인구"].round().astype("Int64")
    )

    return ranking_df[
        ["순위", "지역", "고령화율(%)", "전체 인구", "65세 이상"]
    ]


# ------------------------------------------------------------
# 8. 앱 화면
# ------------------------------------------------------------

st.title("🗺️ 전국 시군구별 고령화 지도")
st.caption("시군구별 전체 인구에서 65세 이상 인구가 차지하는 비율")

try:
    with st.spinner("전국 인구와 지도 경계 데이터를 불러오는 중입니다."):
        population_df = load_population_data(POPULATION_URL)
        geojson = load_geojson(GEOJSON_URL)
        aging_df, latest_year = prepare_aging_data(population_df)
        map_df = prepare_map_data(geojson, aging_df)

    matched_count = int(map_df["고령화율"].notna().sum())
    total_region_count = len(map_df)
    national_population = map_df["전체인구"].sum()
    national_senior_population = map_df["65세이상인구"].sum()

    national_aging_rate = (
        national_senior_population / national_population * 100
        if national_population > 0
        else np.nan
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("기준 연도", f"{latest_year}년")
    metric_col2.metric(
        "전국 고령화율",
        f"{national_aging_rate:.1f}%"
        if pd.notna(national_aging_rate)
        else "-",
    )
    metric_col3.metric(
        "지도 연결 지역",
        f"{matched_count} / {total_region_count}개",
    )

    if matched_count < total_region_count:
        missing_regions = map_df.loc[
            map_df["고령화율"].isna(),
            ["시도", "시군구", "코드"],
        ]

        with st.expander(
            f"인구 데이터가 연결되지 않은 지역 "
            f"{total_region_count - matched_count}개 보기"
        ):
            st.dataframe(
                missing_regions,
                hide_index=True,
                use_container_width=True,
            )

    map_figure = create_choropleth(map_df, geojson)
    st.plotly_chart(
        map_figure,
        use_container_width=True,
        config={"displaylogo": False, "scrollZoom": False},
    )

    # --------------------------------------------------------
    # 향후 50년 시뮬레이션 버튼과 애니메이션
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:10px;
            margin-bottom:10px;
            font-size:18px;
            font-weight:600;
        ">
            지금의 인구 변화가 계속된다면, 50년 뒤 우리 지역은 어떻게 변할까요?
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "show_population_animation" not in st.session_state:
        st.session_state["show_population_animation"] = False

    button_left, button_center, button_right = st.columns([1, 2, 1])

    with button_center:
        button_label = (
            "▲ 인구 변화 시뮬레이션 닫기"
            if st.session_state["show_population_animation"]
            else "⚠ 향후 50년 인구 소멸 시뮬레이션 보기"
        )

        if st.button(
            button_label,
            use_container_width=True,
            type="primary",
        ):
            st.session_state["show_population_animation"] = (
                not st.session_state["show_population_animation"]
            )
            st.rerun()

    if st.session_state["show_population_animation"]:
        st.warning(
            "이 지도는 공식 장래인구추계가 아닙니다. "
            "2015년부터 최신 연도까지의 인구 증감 추세가 "
            "앞으로도 계속된다고 가정한 시각적 시뮬레이션입니다."
        )

        with st.spinner("향후 50년의 인구 변화 장면을 계산하고 있습니다."):
            projection_df, projection_start_year, projection_end_year = (
                prepare_population_projection(
                    population_df=population_df,
                    geojson=geojson,
                    years_ahead=50,
                )
            )
            population_animation = create_population_extinction_animation(
                projection_df=projection_df,
                geojson=geojson,
            )

        st.subheader(
            f"{projection_start_year}년부터 "
            f"{projection_end_year}년까지의 인구 변화"
        )

        st.plotly_chart(
            population_animation,
            use_container_width=True,
            config={"displaylogo": False, "scrollZoom": False},
        )

        st.caption(
            "색이 진한 붉은색으로 변할수록 현재보다 인구가 크게 감소한 지역입니다."
        )

    st.divider()

    # --------------------------------------------------------
    # 고령화율 상위·하위 표
    # --------------------------------------------------------

    high_ranking = make_ranking_table(map_df, ascending=False)
    low_ranking = make_ranking_table(map_df, ascending=True)

    left_column, right_column = st.columns(2, gap="large")

    table_columns = {
        "순위": st.column_config.NumberColumn("순위", format="%d위"),
        "고령화율(%)": st.column_config.NumberColumn(
            "고령화율",
            format="%.1f%%",
        ),
        "전체 인구": st.column_config.NumberColumn(
            "전체 인구",
            format="%d명",
        ),
        "65세 이상": st.column_config.NumberColumn(
            "65세 이상",
            format="%d명",
        ),
    }

    with left_column:
        st.subheader("고령화율이 높은 지역 10곳")
        st.dataframe(
            high_ranking,
            hide_index=True,
            use_container_width=True,
            column_config=table_columns,
        )

    with right_column:
        st.subheader("고령화율이 낮은 지역 10곳")
        st.dataframe(
            low_ranking,
            hide_index=True,
            use_container_width=True,
            column_config=table_columns,
        )

    st.caption(
        "고령화율 = 시군구의 65세 이상 인구 ÷ 시군구 전체 인구 × 100"
    )

except requests.RequestException as error:
    st.error("인터넷에서 데이터를 내려받지 못했습니다.")
    st.exception(error)

except Exception as error:
    st.error("데이터를 처리하거나 지도를 만드는 중 오류가 발생했습니다.")
    st.exception(error)
