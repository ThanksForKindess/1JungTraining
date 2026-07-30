# main.py
# ------------------------------------------------------------
# 전국 시군구별 65세 이상 인구 비율을 보여 주는 Streamlit 앱
# ------------------------------------------------------------

import io
import json
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


# 지도에 표시할 5단계 구간
AGE_GROUP_ORDER = [
    "19% 미만",
    "19% 이상 23% 미만",
    "23% 이상 28% 미만",
    "28% 이상 38% 미만",
    "38% 이상",
]

# 낮은 비율은 옅게, 높은 비율은 진하게 표시
COLOR_MAP = {
    "19% 미만": "#fff7bc",
    "19% 이상 23% 미만": "#fee391",
    "23% 이상 28% 미만": "#fec44f",
    "28% 이상 38% 미만": "#fe9929",
    "38% 이상": "#cc4c02",
}


# ------------------------------------------------------------
# 2. 데이터 불러오기
# ------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_population_data(url: str) -> pd.DataFrame:
    """
    압축된 인구 CSV 파일을 인터넷에서 내려받습니다.

    코드 열은 숫자가 아닌 지역 식별자이므로 반드시 문자열로 읽습니다.
    숫자로 읽으면 앞자리 0이 사라질 수 있습니다.
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    return pd.read_csv(
        io.BytesIO(response.content),
        compression="gzip",
        dtype={"코드": "string"},
        low_memory=False,
    )


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_geojson(url: str) -> dict:
    """전국 시군구 경계 GeoJSON을 내려받습니다."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    return response.json()


# ------------------------------------------------------------
# 3. 인구 열 찾기
# ------------------------------------------------------------

def get_age_from_column(column_name: str):
    """
    '계_65세' 같은 열 이름에서 나이를 숫자로 꺼냅니다.

    예시
    - 계_65세       → 65
    - 계_100세 이상 → 100
    - 남_65세       → 해당 없음
    """
    if not column_name.startswith("계_"):
        return None

    match = re.fullmatch(r"계_(\d+)세(?: 이상)?", column_name)

    if match is None:
        return None

    return int(match.group(1))


def find_population_columns(df: pd.DataFrame):
    """
    전체 인구 계산에 사용할 '계_' 나이별 열과
    65세 이상 계산에 사용할 열을 찾습니다.
    """
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
        raise ValueError(
            "'계_0세', '계_1세' 형태의 나이별 인구 열을 찾지 못했습니다."
        )

    if not senior_columns:
        raise ValueError("65세 이상 인구 열을 찾지 못했습니다.")

    return total_columns, senior_columns


# ------------------------------------------------------------
# 4. 최신 연도 시군구별 고령화율 계산
# ------------------------------------------------------------

def prepare_aging_data(population_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    최신 연도의 읍·면·동 인구를 시군구 단위로 합산한 뒤
    65세 이상 인구 비율을 계산합니다.
    """
    required_columns = {"연도", "시도", "시군구", "동", "코드"}

    missing_columns = required_columns - set(population_df.columns)

    if missing_columns:
        raise ValueError(
            "인구 데이터에 필요한 열이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )

    df = population_df.copy()

    # 연도에 문자나 빈칸이 섞여 있어도 처리할 수 있도록 숫자로 변환합니다.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])

    if df.empty:
        raise ValueError("사용할 수 있는 연도 데이터가 없습니다.")

    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    # 행정동 코드는 계산용 숫자가 아니라 지역 이름표입니다.
    # 혹시 모를 공백과 '.0'을 제거하고 열 자리 문자열로 맞춥니다.
    df["코드"] = (
        df["코드"]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(10)
    )

    # 행정동 코드 앞 5자리가 시군구 코드입니다.
    df["시군구코드"] = df["코드"].str[:5]

    # 전체 인구와 65세 이상 인구에 사용할 열을 찾습니다.
    total_columns, senior_columns = find_population_columns(df)

    # 쉼표가 들어간 인구 값도 계산할 수 있도록 숫자로 변환합니다.
    numeric_columns = list(dict.fromkeys(total_columns + senior_columns))

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column]
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce",
        ).fillna(0)

    # 각 읍·면·동의 전체 인구와 65세 이상 인구를 계산합니다.
    df["전체인구"] = df[total_columns].sum(axis=1)
    df["65세이상인구"] = df[senior_columns].sum(axis=1)

    # 같은 시군구에 속한 읍·면·동 인구를 모두 합칩니다.
    sigungu_df = (
        df.groupby("시군구코드", as_index=False)
        .agg(
            **{
                "전체인구": ("전체인구", "sum"),
                "65세이상인구": ("65세이상인구", "sum"),
            }
        )
    )

    # 전체 인구가 0인 지역에서는 0으로 나누지 않도록 처리합니다.
    sigungu_df["고령화율"] = np.where(
        sigungu_df["전체인구"] > 0,
        sigungu_df["65세이상인구"] / sigungu_df["전체인구"] * 100,
        np.nan,
    )

    return sigungu_df, latest_year


# ------------------------------------------------------------
# 5. GeoJSON 속성과 인구 데이터를 결합
# ------------------------------------------------------------

def prepare_map_data(
    geojson: dict,
    aging_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    GeoJSON의 코드·시도·시군구 정보를 표로 만든 뒤,
    시군구 코드 기준으로 고령화율을 연결합니다.
    """
    region_rows = []

    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})

        code = str(properties.get("코드", "")).strip().zfill(5)

        region_rows.append(
            {
                "코드": code,
                "시도": properties.get("시도", ""),
                "시군구": properties.get("시군구", ""),
            }
        )

        # GeoJSON 속성의 코드도 항상 5자리 문자열로 통일합니다.
        feature["properties"]["코드"] = code

    region_df = pd.DataFrame(region_rows)

    if region_df.empty:
        raise ValueError("GeoJSON에서 시군구 정보를 찾지 못했습니다.")

    map_df = region_df.merge(
        aging_df,
        how="left",
        left_on="코드",
        right_on="시군구코드",
    )

    # 고령화율을 요청한 5개 구간으로 나눕니다.
    map_df["고령화 단계"] = pd.cut(
        map_df["고령화율"],
        bins=[-np.inf, 19, 23, 28, 38, np.inf],
        labels=AGE_GROUP_ORDER,
        right=False,
    )

    # 화면 표시용 값입니다.
    map_df["고령화율 표시"] = map_df["고령화율"].round(1)
    map_df["전체인구 표시"] = (
        map_df["전체인구"].round().astype("Int64")
    )
    map_df["65세이상인구 표시"] = (
        map_df["65세이상인구"].round().astype("Int64")
    )

    return map_df


# ------------------------------------------------------------
# 6. 단계구분도 만들기
# ------------------------------------------------------------

def create_choropleth(map_df: pd.DataFrame, geojson: dict):
    """
    배경 지도 타일 없이 시군구 경계만 표시하는 단계구분도를 만듭니다.
    """
    # 고령화율이 계산된 지역을 5단계 색상으로 표시합니다.
    drawable_df = map_df.dropna(subset=["고령화율", "고령화 단계"]).copy()

    fig = px.choropleth(
        drawable_df,
        geojson=geojson,
        locations="코드",
        featureidkey="properties.코드",
        color="고령화 단계",
        category_orders={"고령화 단계": AGE_GROUP_ORDER},
        color_discrete_map=COLOR_MAP,
        custom_data=[
            "시군구",
            "시도",
            "고령화율 표시",
        ],
    )

    # 마우스를 올렸을 때 보여 줄 정보입니다.
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

    # 배경 지도 타일이나 위도·경도 축을 표시하지 않습니다.
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
    
            font=dict(
                color="#000000",
                size=13,
            ),
    
            title_font=dict(
                color="#000000",
                size=14,
            ),
        ),
    )

    return fig


# ------------------------------------------------------------
# 7. 순위 표 만들기
# ------------------------------------------------------------

def make_ranking_table(
    map_df: pd.DataFrame,
    ascending: bool,
) -> pd.DataFrame:
    """
    고령화율 상위 또는 하위 10개 지역을 표 형태로 만듭니다.
    """
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
        [
            "순위",
            "지역",
            "고령화율(%)",
            "전체 인구",
            "65세 이상",
        ]
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

    if national_population > 0:
        national_aging_rate = (
            national_senior_population / national_population * 100
        )
    else:
        national_aging_rate = np.nan

    # 최신 연도와 간단한 전국 현황을 보여 줍니다.
    metric_col1, metric_col2, metric_col3 = st.columns(3)

    metric_col1.metric("기준 연도", f"{latest_year}년")
    metric_col2.metric(
        "전국 고령화율",
        (
            f"{national_aging_rate:.1f}%"
            if pd.notna(national_aging_rate)
            else "-"
        ),
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

    # 전국 단계구분도
    map_figure = create_choropleth(map_df, geojson)

    st.plotly_chart(
        map_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )

    st.divider()

    # 상위·하위 10개 표를 나란히 배치합니다.
    high_ranking = make_ranking_table(map_df, ascending=False)
    low_ranking = make_ranking_table(map_df, ascending=True)

    left_column, right_column = st.columns(2, gap="large")

    with left_column:
        st.subheader("고령화율이 높은 지역 10곳")
        st.dataframe(
            high_ranking,
            hide_index=True,
            use_container_width=True,
            column_config={
                "순위": st.column_config.NumberColumn(
                    "순위",
                    format="%d위",
                ),
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
            },
        )

    with right_column:
        st.subheader("고령화율이 낮은 지역 10곳")
        st.dataframe(
            low_ranking,
            hide_index=True,
            use_container_width=True,
            column_config={
                "순위": st.column_config.NumberColumn(
                    "순위",
                    format="%d위",
                ),
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
            },
        )

    st.caption(
        "고령화율 = 시군구의 65세 이상 인구 ÷ 시군구 전체 인구 × 100"
    )

except requests.RequestException as error:
    st.error("인터넷에서 데이터를 내려받지 못했습니다.")
    st.exception(error)

except Exception as error:
    st.error("데이터를 처리하는 중 오류가 발생했습니다.")
    st.exception(error)
