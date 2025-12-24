import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots  # 명시적 import (Constraint 2)
from pathlib import Path
import unicodedata
import io  # Excel 다운로드용 (Constraint 3)

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 스타일 (Constraint 4)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# 한글 폰트 설정 (Streamlit UI 및 Plotly)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
/* 탭 폰트 강조 */
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 1.1rem;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 상수 및 설정 정의
# -----------------------------------------------------------------------------
DATA_DIR = Path("data")

# 학교별 설정 (EC 목표, 색상 등)
SCHOOL_CONFIG = {
    "송도고": {"ec": 1.0, "color": "#1f77b4", "order": 1},
    "하늘고": {"ec": 2.0, "color": "#2ca02c", "order": 2, "desc": "최적 (Target)"},
    "아라고": {"ec": 4.0, "color": "#ff7f0e", "order": 3},
    "동산고": {"ec": 8.0, "color": "#d62728", "order": 4}
}

# -----------------------------------------------------------------------------
# 3. 유틸리티 함수 (Constraint 1: 파일 인식 및 정규화)
# -----------------------------------------------------------------------------
def normalize_str(s):
    """문자열을 NFC로 정규화하여 비교 가능하게 만듦"""
    return unicodedata.normalize('NFC', s) if s else s

def find_file(directory: Path, partial_name: str, extension: str) -> Path:
    """
    디렉토리 내에서 정규화된 이름으로 파일을 찾음 (NFC/NFD 호환)
    """
    if not directory.exists():
        return None
    
    target = normalize_str(partial_name)
    
    for file_path in directory.iterdir():
        if file_path.suffix.lower() == extension.lower():
            # 파일명 정규화 후 비교
            current_name = normalize_str(file_path.stem)
            if target in current_name:
                return file_path
    return None

# -----------------------------------------------------------------------------
# 4. 데이터 로딩 함수 (Constraint 5: 캐싱 및 에러 핸들링)
# -----------------------------------------------------------------------------
@st.cache_data
def load_environment_data():
    """환경 데이터 CSV 로드 및 통합"""
    combined_df = pd.DataFrame()
    
    # 4개 학교 데이터 로드
    for school_name in SCHOOL_CONFIG.keys():
        # 파일 찾기 로직
        file_path = find_file(DATA_DIR, f"{school_name}_환경데이터", ".csv")
        
        if file_path:
            try:
                df = pd.read_csv(file_path)
                # 컬럼명 소문자 통일 및 공백 제거
                df.columns = [c.strip().lower() for c in df.columns]
                df['school'] = school_name
                df['target_ec'] = SCHOOL_CONFIG[school_name]['ec']
                
                # 날짜/시간 변환 (에러 방지)
                if 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'], errors='coerce')
                
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except Exception as e:
                st.error(f"❌ {school_name} 환경 데이터 로드 실패: {e}")
        else:
            # 파일을 못 찾았을 경우 경고하지만 멈추지는 않음 (데이터가 일부만 있을 수 있음)
            st.warning(f"⚠️ '{school_name}' 환경 데이터 파일을 찾을 수 없습니다.")
            
    return combined_df

@st.cache_data
def load_growth_data():
    """생육 데이터 XLSX 로드 및 시트 통합"""
    file_path = find_file(DATA_DIR, "4개교_생육결과데이터", ".xlsx")
    
    if not file_path:
        st.error("❌ '4개교_생육결과데이터.xlsx' 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    combined_df = pd.DataFrame()
    try:
        xls = pd.ExcelFile(file_path)
        for sheet_name in xls.sheet_names:
            normalized_sheet = normalize_str(sheet_name)
            
            # 시트 이름이 학교 이름을 포함하는지 확인
            matched_school = None
            for school in SCHOOL_CONFIG.keys():
                if school in normalized_sheet:
                    matched_school = school
                    break
            
            if matched_school:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                df['school'] = matched_school
                df['target_ec'] = SCHOOL_CONFIG[matched_school]['ec']
                combined_df = pd.concat([combined_df, df], ignore_index=True)
    except Exception as e:
        st.error(f"❌ 생육 데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()
        
    return combined_df

# -----------------------------------------------------------------------------
# 5. Main Application Logic
# -----------------------------------------------------------------------------
def main():
    st.title("🌱 극지식물 최적 EC 농도 연구 대시보드")
    
    # --- 데이터 로딩 ---
    with st.spinner("데이터를 불러오는 중입니다..."):
        env_df = load_environment_data()
        growth_df = load_growth_data()

    if env_df.empty and growth_df.empty:
        st.error("데이터가 없습니다. `data/` 폴더에 파일이 있는지 확인해주세요.")
        return

    # --- 사이드바 ---
    st.sidebar.header("설정")
    
    school_list = ["전체"] + list(SCHOOL_CONFIG.keys())
    selected_school = st.sidebar.selectbox("학교 선택", school_list)
    
    # 필터링 로직
    if selected_school != "전체":
        filtered_env = env_df[env_df['school'] == selected_school]
        filtered_growth = growth_df[growth_df['school'] == selected_school]
    else:
        filtered_env = env_df
        filtered_growth = growth_df

    # --- 탭 구성 ---
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

    # ==========================
    # Tab 1: 실험 개요
    # ==========================
    with tab1:
        st.markdown("### 📌 연구 배경 및 목적")
        st.info("""
        극지식물의 스마트팜 재배를 위한 **최적의 EC(전기전도도) 농도**를 규명하기 위한 연구입니다.
        4개 고등학교(송도고, 하늘고, 아라고, 동산고)에서 각기 다른 EC 조건으로 재배 실험을 수행했습니다.
        """)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 🏫 학교별 실험 조건")
            # 조건 데이터프레임 생성
            condition_data = []
            for school, conf in SCHOOL_CONFIG.items():
                count = len(growth_df[growth_df['school'] == school]) if not growth_df.empty else 0
                condition_data.append({
                    "학교명": school,
                    "목표 EC": conf['ec'],
                    "개체수(n)": count,
                    "비고": conf.get('desc', '-')
                })
            cond_df = pd.DataFrame(condition_data)
            st.dataframe(cond_df, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("#### 💡 주요 지표 요약")
            m1, m2, m3, m4 = st.columns(4)
            
            total_n = len(filtered_growth) if not filtered_growth.empty else 0
            avg_temp = filtered_env['temperature'].mean() if not filtered_env.empty else 0
            avg_hum = filtered_env['humidity'].mean() if not filtered_env.empty else 0
            best_ec = "EC 2.0 (하늘고)" # 하드코딩된 결론 (요구사항 기반)

            m1.metric("총 분석 개체수", f"{total_n}개")
            m2.metric("평균 온도", f"{avg_temp:.1f}°C")
            m3.metric("평균 습도", f"{avg_hum:.1f}%")
            m4.metric("최적 EC 농도", best_ec, delta="Best Condition")

    # ==========================
    # Tab 2: 환경 데이터
    # ==========================
    with tab2:
        st.subheader("🌡️ 학교별 환경 데이터 비교")
        
        if not env_df.empty:
            # 평균 데이터 계산
            env_avg = env_df.groupby('school')[['temperature', 'humidity', 'ph', 'ec', 'target_ec']].mean().reset_index()
            
            # --- 2x2 서브플롯 (Constraint 2) ---
            fig_env = make_subplots(
                rows=2, cols=2,
                subplot_titles=("평균 온도 (°C)", "평균 습도 (%)", "평균 pH", "목표 EC vs 실측 EC"),
                vertical_spacing=0.15
            )

            # 색상 매핑
            colors = [SCHOOL_CONFIG[s]['color'] for s in env_avg['school']]

            # 1. 온도
            fig_env.add_trace(go.Bar(x=env_avg['school'], y=env_avg['temperature'], name="온도", marker_color=colors), row=1, col=1)
            # 2. 습도
            fig_env.add_trace(go.Bar(x=env_avg['school'], y=env_avg['humidity'], name="습도", marker_color=colors), row=1, col=2)
            # 3. pH
            fig_env.add_trace(go.Bar(x=env_avg['school'], y=env_avg['ph'], name="pH", marker_color=colors), row=2, col=1)
            
            # 4. EC (이중 막대)
            fig_env.add_trace(go.Bar(x=env_avg['school'], y=env_avg['target_ec'], name="목표 EC", marker_color='lightgray'), row=2, col=2)
            fig_env.add_trace(go.Bar(x=env_avg['school'], y=env_avg['ec'], name="실측 EC", marker_color=colors, opacity=0.8), row=2, col=2)

            fig_env.update_layout(showlegend=False, height=600, font=dict(family="Noto Sans KR, Malgun Gothic"))
            st.plotly_chart(fig_env, use_container_width=True)
            
            # --- 시계열 데이터 ---
            st.markdown("---")
            st.subheader(f"📈 시계열 변화 ({selected_school})")
            
            if not filtered_env.empty:
                # 색상 지정
                ts_color = SCHOOL_CONFIG[selected_school]['color'] if selected_school != "전체" else None
                
                col_ts1, col_ts2, col_ts3 = st.columns(3)
                
                # 온도 시계열
                fig_t = px.line(filtered_env, x='time', y='temperature', color='school', title="온도 변화")
                fig_t.update_layout(font=dict(family="Noto Sans KR, Malgun Gothic"))
                col_ts1.plotly_chart(fig_t, use_container_width=True)
                
                # 습도 시계열
                fig_h = px.line(filtered_env, x='time', y='humidity', color='school', title="습도 변화")
                fig_h.update_layout(font=dict(family="Noto Sans KR, Malgun Gothic"))
                col_ts2.plotly_chart(fig_h, use_container_width=True)

                # EC 시계열 (목표선 추가)
                fig_e = px.line(filtered_env, x='time', y='ec', color='school', title="EC 변화")
                if selected_school != "전체":
                    target = SCHOOL_CONFIG[selected_school]['ec']
                    fig_e.add_hline(y=target, line_dash="dash", annotation_text=f"Target {target}")
                fig_e.update_layout(font=dict(family="Noto Sans KR, Malgun Gothic"))
                col_ts3.plotly_chart(fig_e, use_container_width=True)
            else:
                st.info("선택된 학교의 시계열 데이터가 없습니다.")

            # --- 데이터 다운로드 ---
            with st.expander("💾 환경 데이터 원본 보기 및 다운로드"):
                st.dataframe(filtered_env)
                csv = filtered_env.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "CSV 다운로드",
                    data=csv,
                    file_name="env_data.csv",
                    mime="text/csv"
                )
        else:
            st.warning("환경 데이터가 로드되지 않았습니다.")

    # ==========================
    # Tab 3: 생육 결과
    # ==========================
    with tab3:
        st.subheader("📊 EC 농도별 생육 결과 비교")
        
        if not growth_df.empty:
            # 컬럼 매핑 (데이터셋에 따라 이름이 약간 다를 수 있으므로 확인 필요)
            # 여기서는 [잎 수(장), 지상부 길이(mm), 지하부길이(mm), 생중량(g)] 가정
            
            # 컬럼명 정리 (유사도 매칭 또는 하드코딩된 키워드 사용)
            cols = growth_df.columns
            fw_col = next((c for c in cols if "생중량" in c), None)
            leaf_col = next((c for c in cols if "잎" in c), None)
            len_top_col = next((c for c in cols if "지상부" in c), None)
            
            if fw_col:
                # 핵심 지표 카드
                best_school_row = growth_df.loc[growth_df[fw_col].idxmax()]
                avg_fw_by_ec = growth_df.groupby('school')[fw_col].mean()
                max_avg_school = avg_fw_by_ec.idxmax()
                
                st.markdown(f"""
                <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; border-left: 5px solid #2ca02c;">
                    <h3>🥇 핵심 결과 요약</h3>
                    <p>평균 생중량이 가장 높은 조건은 <b>{max_avg_school} (EC {SCHOOL_CONFIG[max_avg_school]['ec']})</b> 입니다.</p>
                </div>
                <br>
                """, unsafe_allow_html=True)
                
                # --- 2x2 서브플롯: 생육 비교 ---
                growth_avg = growth_df.groupby('school').mean(numeric_only=True).reset_index()
                
                fig_growth = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=("평균 생중량 (g) ⭐", "평균 잎 수 (장)", "평균 지상부 길이 (mm)", "개체수 (n)"),
                    vertical_spacing=0.15
                )
                
                colors_g = [SCHOOL_CONFIG[s]['color'] for s in growth_avg['school']]
                
                # 1. 생중량
                fig_growth.add_trace(go.Bar(x=growth_avg['school'], y=growth_avg[fw_col], name="생중량", marker_color=colors_g), row=1, col=1)
                # 2. 잎 수
                if leaf_col:
                    fig_growth.add_trace(go.Bar(x=growth_avg['school'], y=growth_avg[leaf_col], name="잎 수", marker_color=colors_g), row=1, col=2)
                # 3. 지상부 길이
                if len_top_col:
                    fig_growth.add_trace(go.Bar(x=growth_avg['school'], y=growth_avg[len_top_col], name="길이", marker_color=colors_g), row=2, col=1)
                # 4. 개체수
                count_df = growth_df['school'].value_counts().reset_index()
                count_df.columns = ['school', 'count']
                fig_growth.add_trace(go.Bar(x=count_df['school'], y=count_df['count'], name="개체수", marker_color='gray'), row=2, col=2)

                fig_growth.update_layout(showlegend=False, height=600, font=dict(family="Noto Sans KR, Malgun Gothic"))
                st.plotly_chart(fig_growth, use_container_width=True)

                # --- 분포 및 상관관계 ---
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    st.markdown("#### 📦 학교별 생중량 분포")
                    fig_box = px.box(filtered_growth, x='school', y=fw_col, color='school', 
                                     color_discrete_map={k: v['color'] for k, v in SCHOOL_CONFIG.items()})
                    fig_box.update_layout(showlegend=False, font=dict(family="Noto Sans KR, Malgun Gothic"))
                    st.plotly_chart(fig_box, use_container_width=True)

                with col_g2:
                    st.markdown("#### 🔗 상관관계: 잎 수 vs 생중량")
                    if leaf_col and fw_col:
                        fig_scatter = px.scatter(filtered_growth, x=leaf_col, y=fw_col, color='school',
                                                trendline="ols",
                                                color_discrete_map={k: v['color'] for k, v in SCHOOL_CONFIG.items()})
                        fig_scatter.update_layout(font=dict(family="Noto Sans KR, Malgun Gothic"))
                        st.plotly_chart(fig_scatter, use_container_width=True)

            # --- Excel 다운로드 (Constraint 3) ---
            with st.expander("💾 생육 데이터 원본 보기 및 다운로드"):
                st.dataframe(filtered_growth)
                
                # BytesIO를 사용한 Excel 저장
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    filtered_growth.to_excel(writer, index=False, sheet_name='Growth_Data')
                
                buffer.seek(0)
                
                st.download_button(
                    label="Excel 다운로드",
                    data=buffer,
                    file_name="growth_data_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        else:
            st.warning("생육 데이터가 로드되지 않았습니다.")

if __name__ == "__main__":
    main()

# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# import plotly.express as px
# from pathlib import Path
# import unicodedata
# import io

# # 페이지 설정
# st.set_page_config(
#     page_title="극지식물 최적 EC 농도 연구",
#     page_icon="🌱",
#     layout="wide"
# )

# # 한글 폰트 설정
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
# html, body, [class*="css"] {
#     font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
# }
# </style>
# """, unsafe_allow_html=True)

# # 학교별 EC 정보
# SCHOOL_INFO = {
#     "송도고": {"ec": 1.0, "color": "#FF6B6B"},
#     "하늘고": {"ec": 2.0, "color": "#4ECDC4"},
#     "아라고": {"ec": 4.0, "color": "#95E1D3"},
#     "동산고": {"ec": 8.0, "color": "#FFA07A"}
# }

# # 데이터 로딩 함수
# @st.cache_data
# def load_env_data():
#     """환경 데이터 로딩 (CSV 파일들)"""
#     data_path = Path("data")
#     env_data = {}
    
#     if not data_path.exists():
#         st.error("❌ data 폴더를 찾을 수 없습니다!")
#         return env_data
    
#     # CSV 파일 찾기 (NFC/NFD 대응)
#     for file_path in data_path.iterdir():
#         if file_path.suffix.lower() == '.csv':
#             # 파일명 정규화하여 학교명 추출
#             filename_nfc = unicodedata.normalize("NFC", file_path.name)
#             filename_nfd = unicodedata.normalize("NFD", file_path.name)
            
#             for school in SCHOOL_INFO.keys():
#                 school_nfc = unicodedata.normalize("NFC", school)
#                 school_nfd = unicodedata.normalize("NFD", school)
                
#                 if (school_nfc in filename_nfc or school_nfd in filename_nfd or
#                     school_nfc in filename_nfd or school_nfd in filename_nfc):
#                     try:
#                         df = pd.read_csv(file_path)
#                         env_data[school] = df
#                         break
#                     except Exception as e:
#                         st.error(f"❌ {file_path.name} 로딩 실패: {e}")
    
#     return env_data

# @st.cache_data
# def load_growth_data():
#     """생육 결과 데이터 로딩 (XLSX 파일)"""
#     data_path = Path("data")
#     growth_data = {}
    
#     if not data_path.exists():
#         st.error("❌ data 폴더를 찾을 수 없습니다!")
#         return growth_data
    
#     # XLSX 파일 찾기
#     xlsx_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
    
#     if not xlsx_files:
#         st.error("❌ 생육 결과 데이터 파일(.xlsx)을 찾을 수 없습니다!")
#         return growth_data
    
#     # 첫 번째 XLSX 파일 사용
#     xlsx_file = xlsx_files[0]
    
#     try:
#         # 모든 시트 읽기
#         excel_file = pd.ExcelFile(xlsx_file)
        
#         for sheet_name in excel_file.sheet_names:
#             # 시트명 정규화
#             sheet_nfc = unicodedata.normalize("NFC", sheet_name)
#             sheet_nfd = unicodedata.normalize("NFD", sheet_name)
            
#             for school in SCHOOL_INFO.keys():
#                 school_nfc = unicodedata.normalize("NFC", school)
#                 school_nfd = unicodedata.normalize("NFD", school)
                
#                 if (school_nfc in sheet_nfc or school_nfd in sheet_nfd or
#                     school_nfc in sheet_nfd or school_nfd in sheet_nfc):
#                     df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
#                     growth_data[school] = df
#                     break
        
#     except Exception as e:
#         st.error(f"❌ XLSX 파일 로딩 실패: {e}")
    
#     return growth_data

# # 메인 앱
# def main():
#     st.title("🌱 극지식물 최적 EC 농도 연구")
    
#     # 데이터 로딩
#     with st.spinner("📊 데이터 로딩 중..."):
#         env_data = load_env_data()
#         growth_data = load_growth_data()
    
#     if not env_data and not growth_data:
#         st.error("❌ 데이터를 불러올 수 없습니다. data 폴더와 파일들을 확인해주세요.")
#         return
    
#     # 사이드바
#     st.sidebar.title("🔬 분석 옵션")
#     schools = ["전체"] + list(SCHOOL_INFO.keys())
#     selected_school = st.sidebar.selectbox("학교 선택", schools)
    
#     # 탭 생성
#     tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])
    
#     # Tab 1: 실험 개요
#     with tab1:
#         st.header("📖 실험 개요")
        
#         st.markdown("""
#         ### 연구 배경 및 목적
#         - **목표**: 극지식물(남극좁쌀풀) 재배를 위한 최적 EC 농도 도출
#         - **방법**: 4개 학교에서 서로 다른 EC 농도 조건으로 재배 실험 진행
#         - **측정**: 환경 데이터(온도, 습도, pH, EC) 및 생육 결과(생중량, 잎 수, 길이) 수집
#         """)
        
#         # 학교별 EC 조건 표
#         st.subheader("🏫 학교별 EC 조건")
        
#         school_info_df = pd.DataFrame([
#             {
#                 "학교명": school,
#                 "EC 목표 (dS/m)": info["ec"],
#                 "개체수": len(growth_data.get(school, [])),
#                 "색상": info["color"]
#             }
#             for school, info in SCHOOL_INFO.items()
#         ])
        
#         st.dataframe(
#             school_info_df.style.apply(
#                 lambda x: [f"background-color: {SCHOOL_INFO[x['학교명']]['color']}33" 
#                           for _ in x], axis=1
#             ),
#             hide_index=True,
#             use_container_width=True
#         )
        
#         # 주요 지표 카드
#         st.subheader("📊 주요 지표")
#         col1, col2, col3, col4 = st.columns(4)
        
#         total_samples = sum(len(df) for df in growth_data.values())
        
#         if env_data:
#             avg_temp = sum(df['temperature'].mean() for df in env_data.values()) / len(env_data)
#             avg_humidity = sum(df['humidity'].mean() for df in env_data.values()) / len(env_data)
#         else:
#             avg_temp = 0
#             avg_humidity = 0
        
#         # 최적 EC 찾기 (생중량 기준)
#         optimal_ec = "2.0 (하늘고)"
#         if growth_data:
#             avg_weights = {}
#             for school, df in growth_data.items():
#                 if '생중량(g)' in df.columns:
#                     avg_weights[school] = df['생중량(g)'].mean()
#             if avg_weights:
#                 optimal_school = max(avg_weights, key=avg_weights.get)
#                 optimal_ec = f"{SCHOOL_INFO[optimal_school]['ec']} ({optimal_school})"
        
#         col1.metric("총 개체수", f"{total_samples}개")
#         col2.metric("평균 온도", f"{avg_temp:.1f}°C")
#         col3.metric("평균 습도", f"{avg_humidity:.1f}%")
#         col4.metric("최적 EC", optimal_ec)
    
#     # Tab 2: 환경 데이터
#     with tab2:
#         st.header("🌡️ 환경 데이터 분석")
        
#         if not env_data:
#             st.warning("⚠️ 환경 데이터를 불러올 수 없습니다.")
#             return
        
#         # 학교별 환경 평균 비교 (2x2 서브플롯)
#         st.subheader("📈 학교별 환경 평균 비교")
        
#         fig = make_subplots(
#             rows=2, cols=2,
#             subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"),
#             vertical_spacing=0.15,
#             horizontal_spacing=0.1
#         )
        
#         schools_list = list(env_data.keys())
#         colors = [SCHOOL_INFO[s]["color"] for s in schools_list]
        
#         # 평균 계산
#         avg_temps = [env_data[s]['temperature'].mean() for s in schools_list]
#         avg_humids = [env_data[s]['humidity'].mean() for s in schools_list]
#         avg_phs = [env_data[s]['ph'].mean() for s in schools_list]
#         avg_ecs = [env_data[s]['ec'].mean() for s in schools_list]
#         target_ecs = [SCHOOL_INFO[s]['ec'] for s in schools_list]
        
#         # 온도
#         fig.add_trace(
#             go.Bar(x=schools_list, y=avg_temps, marker_color=colors, name="온도",
#                    showlegend=False),
#             row=1, col=1
#         )
        
#         # 습도
#         fig.add_trace(
#             go.Bar(x=schools_list, y=avg_humids, marker_color=colors, name="습도",
#                    showlegend=False),
#             row=1, col=2
#         )
        
#         # pH
#         fig.add_trace(
#             go.Bar(x=schools_list, y=avg_phs, marker_color=colors, name="pH",
#                    showlegend=False),
#             row=2, col=1
#         )
        
#         # EC 비교
#         fig.add_trace(
#             go.Bar(x=schools_list, y=target_ecs, name="목표 EC", marker_color="lightblue"),
#             row=2, col=2
#         )
#         fig.add_trace(
#             go.Bar(x=schools_list, y=avg_ecs, name="실측 EC", marker_color=colors),
#             row=2, col=2
#         )
        
#         fig.update_xaxes(title_text="학교", row=2, col=1)
#         fig.update_xaxes(title_text="학교", row=2, col=2)
#         fig.update_yaxes(title_text="온도 (°C)", row=1, col=1)
#         fig.update_yaxes(title_text="습도 (%)", row=1, col=2)
#         fig.update_yaxes(title_text="pH", row=2, col=1)
#         fig.update_yaxes(title_text="EC (dS/m)", row=2, col=2)
        
#         fig.update_layout(
#             height=600,
#             font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
#             showlegend=True
#         )
        
#         st.plotly_chart(fig, use_container_width=True)
        
#         # 선택한 학교 시계열
#         if selected_school != "전체" and selected_school in env_data:
#             st.subheader(f"📉 {selected_school} 환경 데이터 시계열")
            
#             df = env_data[selected_school].copy()
            
#             # 온도 변화
#             fig_temp = go.Figure()
#             fig_temp.add_trace(go.Scatter(
#                 x=df.index, y=df['temperature'],
#                 mode='lines', name='온도',
#                 line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
#             ))
#             fig_temp.update_layout(
#                 title="온도 변화",
#                 xaxis_title="측정 시점",
#                 yaxis_title="온도 (°C)",
#                 height=300,
#                 font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#             )
#             st.plotly_chart(fig_temp, use_container_width=True)
            
#             # 습도 변화
#             fig_humid = go.Figure()
#             fig_humid.add_trace(go.Scatter(
#                 x=df.index, y=df['humidity'],
#                 mode='lines', name='습도',
#                 line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
#             ))
#             fig_humid.update_layout(
#                 title="습도 변화",
#                 xaxis_title="측정 시점",
#                 yaxis_title="습도 (%)",
#                 height=300,
#                 font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#             )
#             st.plotly_chart(fig_humid, use_container_width=True)
            
#             # EC 변화
#             fig_ec = go.Figure()
#             fig_ec.add_trace(go.Scatter(
#                 x=df.index, y=df['ec'],
#                 mode='lines', name='실측 EC',
#                 line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
#             ))
#             fig_ec.add_hline(
#                 y=SCHOOL_INFO[selected_school]['ec'],
#                 line_dash="dash",
#                 line_color="red",
#                 annotation_text=f"목표 EC: {SCHOOL_INFO[selected_school]['ec']}"
#             )
#             fig_ec.update_layout(
#                 title="EC 변화",
#                 xaxis_title="측정 시점",
#                 yaxis_title="EC (dS/m)",
#                 height=300,
#                 font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#             )
#             st.plotly_chart(fig_ec, use_container_width=True)
        
#         # 환경 데이터 원본
#         with st.expander("📋 환경 데이터 원본"):
#             if selected_school == "전체":
#                 for school, df in env_data.items():
#                     st.subheader(school)
#                     st.dataframe(df, use_container_width=True)
                    
#                     # CSV 다운로드
#                     csv = df.to_csv(index=False).encode('utf-8-sig')
#                     st.download_button(
#                         label=f"📥 {school} CSV 다운로드",
#                         data=csv,
#                         file_name=f"{school}_환경데이터.csv",
#                         mime="text/csv"
#                     )
#             else:
#                 if selected_school in env_data:
#                     st.dataframe(env_data[selected_school], use_container_width=True)
#                     csv = env_data[selected_school].to_csv(index=False).encode('utf-8-sig')
#                     st.download_button(
#                         label=f"📥 CSV 다운로드",
#                         data=csv,
#                         file_name=f"{selected_school}_환경데이터.csv",
#                         mime="text/csv"
#                     )
    
#     # Tab 3: 생육 결과
#     with tab3:
#         st.header("📊 생육 결과 분석")
        
#         if not growth_data:
#             st.warning("⚠️ 생육 결과 데이터를 불러올 수 없습니다.")
#             return
        
#         # 핵심 결과 카드: EC별 평균 생중량
#         st.subheader("🥇 핵심 결과: EC별 평균 생중량")
        
#         avg_weights_by_ec = {}
#         for school, df in growth_data.items():
#             if '생중량(g)' in df.columns:
#                 ec = SCHOOL_INFO[school]['ec']
#                 avg_weight = df['생중량(g)'].mean()
#                 avg_weights_by_ec[f"EC {ec} ({school})"] = avg_weight
        
#         if avg_weights_by_ec:
#             col1, col2, col3, col4 = st.columns(4)
#             cols = [col1, col2, col3, col4]
            
#             max_weight = max(avg_weights_by_ec.values())
            
#             for idx, (label, weight) in enumerate(sorted(avg_weights_by_ec.items())):
#                 is_max = weight == max_weight
#                 cols[idx].metric(
#                     label,
#                     f"{weight:.3f}g",
#                     delta="⭐ 최적" if is_max else None,
#                     delta_color="normal" if is_max else "off"
#                 )
        
#         # EC별 생육 비교 (2x2)
#         st.subheader("📊 EC별 생육 비교")
        
#         fig2 = make_subplots(
#             rows=2, cols=2,
#             subplot_titles=("⭐ 평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수 비교"),
#             vertical_spacing=0.15,
#             horizontal_spacing=0.1
#         )
        
#         schools_list = list(growth_data.keys())
#         colors = [SCHOOL_INFO[s]["color"] for s in schools_list]
        
#         # 평균 계산
#         avg_weights = []
#         avg_leaves = []
#         avg_heights = []
#         sample_counts = []
        
#         for school in schools_list:
#             df = growth_data[school]
#             avg_weights.append(df['생중량(g)'].mean() if '생중량(g)' in df.columns else 0)
#             avg_leaves.append(df['잎 수(장)'].mean() if '잎 수(장)' in df.columns else 0)
#             avg_heights.append(df['지상부 길이(mm)'].mean() if '지상부 길이(mm)' in df.columns else 0)
#             sample_counts.append(len(df))
        
#         # 생중량
#         fig2.add_trace(
#             go.Bar(x=schools_list, y=avg_weights, marker_color=colors, showlegend=False),
#             row=1, col=1
#         )
        
#         # 잎 수
#         fig2.add_trace(
#             go.Bar(x=schools_list, y=avg_leaves, marker_color=colors, showlegend=False),
#             row=1, col=2
#         )
        
#         # 지상부 길이
#         fig2.add_trace(
#             go.Bar(x=schools_list, y=avg_heights, marker_color=colors, showlegend=False),
#             row=2, col=1
#         )
        
#         # 개체수
#         fig2.add_trace(
#             go.Bar(x=schools_list, y=sample_counts, marker_color=colors, showlegend=False),
#             row=2, col=2
#         )
        
#         fig2.update_xaxes(title_text="학교", row=2, col=1)
#         fig2.update_xaxes(title_text="학교", row=2, col=2)
#         fig2.update_yaxes(title_text="생중량 (g)", row=1, col=1)
#         fig2.update_yaxes(title_text="잎 수 (장)", row=1, col=2)
#         fig2.update_yaxes(title_text="길이 (mm)", row=2, col=1)
#         fig2.update_yaxes(title_text="개체수", row=2, col=2)
        
#         fig2.update_layout(
#             height=600,
#             font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#         )
        
#         st.plotly_chart(fig2, use_container_width=True)
        
#         # 학교별 생중량 분포
#         st.subheader("📦 학교별 생중량 분포")
        
#         fig_box = go.Figure()
#         for school in schools_list:
#             df = growth_data[school]
#             if '생중량(g)' in df.columns:
#                 fig_box.add_trace(go.Box(
#                     y=df['생중량(g)'],
#                     name=school,
#                     marker_color=SCHOOL_INFO[school]['color']
#                 ))
        
#         fig_box.update_layout(
#             yaxis_title="생중량 (g)",
#             height=400,
#             font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#         )
        
#         st.plotly_chart(fig_box, use_container_width=True)
        
#         # 상관관계 분석
#         st.subheader("🔗 상관관계 분석")
        
#         col1, col2 = st.columns(2)
        
#         # 모든 데이터 합치기
#         all_data = []
#         for school, df in growth_data.items():
#             df_copy = df.copy()
#             df_copy['학교'] = school
#             df_copy['EC'] = SCHOOL_INFO[school]['ec']
#             all_data.append(df_copy)
        
#         combined_df = pd.concat(all_data, ignore_index=True)
        
#         with col1:
#             if '잎 수(장)' in combined_df.columns and '생중량(g)' in combined_df.columns:
#                 fig_corr1 = px.scatter(
#                     combined_df,
#                     x='잎 수(장)',
#                     y='생중량(g)',
#                     color='학교',
#                     color_discrete_map={s: SCHOOL_INFO[s]['color'] for s in schools_list},
#                     title="잎 수 vs 생중량",
#                     trendline="ols"
#                 )
#                 fig_corr1.update_layout(
#                     height=400,
#                     font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#                 )
#                 st.plotly_chart(fig_corr1, use_container_width=True)
        
#         with col2:
#             if '지상부 길이(mm)' in combined_df.columns and '생중량(g)' in combined_df.columns:
#                 fig_corr2 = px.scatter(
#                     combined_df,
#                     x='지상부 길이(mm)',
#                     y='생중량(g)',
#                     color='학교',
#                     color_discrete_map={s: SCHOOL_INFO[s]['color'] for s in schools_list},
#                     title="지상부 길이 vs 생중량",
#                     trendline="ols"
#                 )
#                 fig_corr2.update_layout(
#                     height=400,
#                     font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
#                 )
#                 st.plotly_chart(fig_corr2, use_container_width=True)
        
#         # 생육 데이터 원본
#         with st.expander("📋 생육 데이터 원본"):
#             if selected_school == "전체":
#                 for school, df in growth_data.items():
#                     st.subheader(school)
#                     st.dataframe(df, use_container_width=True)
                
#                 # 전체 XLSX 다운로드
#                 buffer = io.BytesIO()
#                 with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#                     for school, df in growth_data.items():
#                         df.to_excel(writer, sheet_name=school, index=False)
#                 buffer.seek(0)
                
#                 st.download_button(
#                     label="📥 전체 생육 데이터 XLSX 다운로드",
#                     data=buffer,
#                     file_name="전체_생육결과데이터.xlsx",
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#                 )
#             else:
#                 if selected_school in growth_data:
#                     st.dataframe(growth_data[selected_school], use_container_width=True)
                    
#                     buffer = io.BytesIO()
#                     growth_data[selected_school].to_excel(buffer, index=False, engine='openpyxl')
#                     buffer.seek(0)
                    
#                     st.download_button(
#                         label=f"📥 {selected_school} XLSX 다운로드",
#                         data=buffer,
#                         file_name=f"{selected_school}_생육결과.xlsx",
#                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#                     )

# if __name__ == "__main__":
#     main()
