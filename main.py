import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
import unicodedata
import io

# 페이지 설정
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# 한글 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 EC 정보
SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#FF6B6B"},
    "하늘고": {"ec": 2.0, "color": "#4ECDC4"},
    "아라고": {"ec": 4.0, "color": "#95E1D3"},
    "동산고": {"ec": 8.0, "color": "#FFA07A"}
}

# 데이터 로딩 함수
@st.cache_data
def load_env_data():
    """환경 데이터 로딩 (CSV 파일들)"""
    data_path = Path("data")
    env_data = {}
    
    if not data_path.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다!")
        return env_data
    
    # CSV 파일 찾기 (NFC/NFD 대응)
    for file_path in data_path.iterdir():
        if file_path.suffix.lower() == '.csv':
            # 파일명 정규화하여 학교명 추출
            filename_nfc = unicodedata.normalize("NFC", file_path.name)
            filename_nfd = unicodedata.normalize("NFD", file_path.name)
            
            for school in SCHOOL_INFO.keys():
                school_nfc = unicodedata.normalize("NFC", school)
                school_nfd = unicodedata.normalize("NFD", school)
                
                if (school_nfc in filename_nfc or school_nfd in filename_nfd or
                    school_nfc in filename_nfd or school_nfd in filename_nfc):
                    try:
                        df = pd.read_csv(file_path)
                        env_data[school] = df
                        break
                    except Exception as e:
                        st.error(f"❌ {file_path.name} 로딩 실패: {e}")
    
    return env_data

@st.cache_data
def load_growth_data():
    """생육 결과 데이터 로딩 (XLSX 파일)"""
    data_path = Path("data")
    growth_data = {}
    
    if not data_path.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다!")
        return growth_data
    
    # XLSX 파일 찾기
    xlsx_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
    
    if not xlsx_files:
        st.error("❌ 생육 결과 데이터 파일(.xlsx)을 찾을 수 없습니다!")
        return growth_data
    
    # 첫 번째 XLSX 파일 사용
    xlsx_file = xlsx_files[0]
    
    try:
        # 모든 시트 읽기
        excel_file = pd.ExcelFile(xlsx_file)
        
        for sheet_name in excel_file.sheet_names:
            # 시트명 정규화
            sheet_nfc = unicodedata.normalize("NFC", sheet_name)
            sheet_nfd = unicodedata.normalize("NFD", sheet_name)
            
            for school in SCHOOL_INFO.keys():
                school_nfc = unicodedata.normalize("NFC", school)
                school_nfd = unicodedata.normalize("NFD", school)
                
                if (school_nfc in sheet_nfc or school_nfd in sheet_nfd or
                    school_nfc in sheet_nfd or school_nfd in sheet_nfc):
                    df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
                    growth_data[school] = df
                    break
        
    except Exception as e:
        st.error(f"❌ XLSX 파일 로딩 실패: {e}")
    
    return growth_data

# 메인 앱
def main():
    st.title("🌱 극지식물 최적 EC 농도 연구")
    
    # 데이터 로딩
    with st.spinner("📊 데이터 로딩 중..."):
        env_data = load_env_data()
        growth_data = load_growth_data()
    
    if not env_data and not growth_data:
        st.error("❌ 데이터를 불러올 수 없습니다. data 폴더와 파일들을 확인해주세요.")
        return
    
    # 사이드바
    st.sidebar.title("🔬 분석 옵션")
    schools = ["전체"] + list(SCHOOL_INFO.keys())
    selected_school = st.sidebar.selectbox("학교 선택", schools)
    
    # 선택에 따라 필터링할 학교 목록 결정
    if selected_school == "전체":
        filtered_schools = list(SCHOOL_INFO.keys())
    else:
        filtered_schools = [selected_school]
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])
    
    # Tab 1: 실험 개요
    with tab1:
        st.header("📖 실험 개요")
        
        st.markdown("""
        ### 연구 배경 및 목적
        - **목표**: 극지식물(남극좁쌀풀) 재배를 위한 최적 EC 농도 도출
        - **방법**: 4개 학교에서 서로 다른 EC 농도 조건으로 재배 실험 진행
        - **측정**: 환경 데이터(온도, 습도, pH, EC) 및 생육 결과(생중량, 잎 수, 길이) 수집
        """)
        
        # 학교별 EC 조건 표
        st.subheader("🏫 학교별 EC 조건")
        
        school_info_df = pd.DataFrame([
            {
                "학교명": school,
                "EC 목표 (dS/m)": info["ec"],
                "개체수": len(growth_data.get(school, [])),
                "색상": info["color"]
            }
            for school, info in SCHOOL_INFO.items()
        ])
        
        st.dataframe(
            school_info_df.style.apply(
                lambda x: [f"background-color: {SCHOOL_INFO[x['학교명']]['color']}33" 
                          for _ in x], axis=1
            ),
            hide_index=True,
            use_container_width=True
        )
        
        # 주요 지표 카드 (선택한 학교에 따라 변경)
        st.subheader("📊 주요 지표")
        col1, col2, col3, col4 = st.columns(4)
        
        # 필터링된 데이터로 계산
        total_samples = sum(len(growth_data[s]) for s in filtered_schools if s in growth_data)
        
        if env_data:
            filtered_env = {s: env_data[s] for s in filtered_schools if s in env_data}
            if filtered_env:
                avg_temp = sum(df['temperature'].mean() for df in filtered_env.values()) / len(filtered_env)
                avg_humidity = sum(df['humidity'].mean() for df in filtered_env.values()) / len(filtered_env)
            else:
                avg_temp = 0
                avg_humidity = 0
        else:
            avg_temp = 0
            avg_humidity = 0
        
        # 최적 EC 찾기 (필터링된 학교 내에서)
        optimal_ec = "-"
        if growth_data:
            avg_weights = {}
            for school in filtered_schools:
                if school in growth_data:
                    df = growth_data[school]
                    if '생중량(g)' in df.columns:
                        avg_weights[school] = df['생중량(g)'].mean()
            if avg_weights:
                optimal_school = max(avg_weights, key=avg_weights.get)
                optimal_ec = f"{SCHOOL_INFO[optimal_school]['ec']} ({optimal_school})"
        
        col1.metric("총 개체수", f"{total_samples}개")
        col2.metric("평균 온도", f"{avg_temp:.1f}°C")
        col3.metric("평균 습도", f"{avg_humidity:.1f}%")
        col4.metric("최적 EC", optimal_ec)
    
    # Tab 2: 환경 데이터
    with tab2:
        st.header("🌡️ 환경 데이터 분석")
        
        if not env_data:
            st.warning("⚠️ 환경 데이터를 불러올 수 없습니다.")
            return
        
        # 학교별 환경 평균 비교 (필터링 적용)
        st.subheader(f"📈 {'전체 ' if selected_school == '전체' else selected_school + ' '}환경 평균 비교")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # 필터링된 학교만 사용
        schools_list = [s for s in filtered_schools if s in env_data]
        colors = [SCHOOL_INFO[s]["color"] for s in schools_list]
        
        # 평균 계산
        avg_temps = [env_data[s]['temperature'].mean() for s in schools_list]
        avg_humids = [env_data[s]['humidity'].mean() for s in schools_list]
        avg_phs = [env_data[s]['ph'].mean() for s in schools_list]
        avg_ecs = [env_data[s]['ec'].mean() for s in schools_list]
        target_ecs = [SCHOOL_INFO[s]['ec'] for s in schools_list]
        
        # 온도
        fig.add_trace(
            go.Bar(x=schools_list, y=avg_temps, marker_color=colors, name="온도",
                   showlegend=False),
            row=1, col=1
        )
        
        # 습도
        fig.add_trace(
            go.Bar(x=schools_list, y=avg_humids, marker_color=colors, name="습도",
                   showlegend=False),
            row=1, col=2
        )
        
        # pH
        fig.add_trace(
            go.Bar(x=schools_list, y=avg_phs, marker_color=colors, name="pH",
                   showlegend=False),
            row=2, col=1
        )
        
        # EC 비교
        fig.add_trace(
            go.Bar(x=schools_list, y=target_ecs, name="목표 EC", marker_color="lightblue"),
            row=2, col=2
        )
        fig.add_trace(
            go.Bar(x=schools_list, y=avg_ecs, name="실측 EC", marker_color=colors),
            row=2, col=2
        )
        
        fig.update_xaxes(title_text="학교", row=2, col=1)
        fig.update_xaxes(title_text="학교", row=2, col=2)
        fig.update_yaxes(title_text="온도 (°C)", row=1, col=1)
        fig.update_yaxes(title_text="습도 (%)", row=1, col=2)
        fig.update_yaxes(title_text="pH", row=2, col=1)
        fig.update_yaxes(title_text="EC (dS/m)", row=2, col=2)
        
        fig.update_layout(
            height=600,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 시계열 (특정 학교 선택 시에만)
        if selected_school != "전체" and selected_school in env_data:
            st.subheader(f"📉 {selected_school} 환경 데이터 시계열")
            
            df = env_data[selected_school].copy()
            
            # 온도 변화
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df.index, y=df['temperature'],
                mode='lines', name='온도',
                line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
            ))
            fig_temp.update_layout(
                title="온도 변화",
                xaxis_title="측정 시점",
                yaxis_title="온도 (°C)",
                height=300,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
            )
            st.plotly_chart(fig_temp, use_container_width=True)
            
            # 습도 변화
            fig_humid = go.Figure()
            fig_humid.add_trace(go.Scatter(
                x=df.index, y=df['humidity'],
                mode='lines', name='습도',
                line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
            ))
            fig_humid.update_layout(
                title="습도 변화",
                xaxis_title="측정 시점",
                yaxis_title="습도 (%)",
                height=300,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
            )
            st.plotly_chart(fig_humid, use_container_width=True)
            
            # EC 변화
            fig_ec = go.Figure()
            fig_ec.add_trace(go.Scatter(
                x=df.index, y=df['ec'],
                mode='lines', name='실측 EC',
                line=dict(color=SCHOOL_INFO[selected_school]['color'], width=2)
            ))
            fig_ec.add_hline(
                y=SCHOOL_INFO[selected_school]['ec'],
                line_dash="dash",
                line_color="red",
                annotation_text=f"목표 EC: {SCHOOL_INFO[selected_school]['ec']}"
            )
            fig_ec.update_layout(
                title="EC 변화",
                xaxis_title="측정 시점",
                yaxis_title="EC (dS/m)",
                height=300,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
            )
            st.plotly_chart(fig_ec, use_container_width=True)
        
        # 환경 데이터 원본
        with st.expander("📋 환경 데이터 원본"):
            if selected_school == "전체":
                for school in filtered_schools:
                    if school in env_data:
                        st.subheader(school)
                        st.dataframe(env_data[school], use_container_width=True)
                        
                        # CSV 다운로드
                        csv = env_data[school].to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label=f"📥 {school} CSV 다운로드",
                            data=csv,
                            file_name=f"{school}_환경데이터.csv",
                            mime="text/csv",
                            key=f"env_csv_{school}"
                        )
            else:
                if selected_school in env_data:
                    st.dataframe(env_data[selected_school], use_container_width=True)
                    csv = env_data[selected_school].to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 CSV 다운로드",
                        data=csv,
                        file_name=f"{selected_school}_환경데이터.csv",
                        mime="text/csv"
                    )
    
    # Tab 3: 생육 결과
    with tab3:
        st.header("📊 생육 결과 분석")
        
        if not growth_data:
            st.warning("⚠️ 생육 결과 데이터를 불러올 수 없습니다.")
            return
        
        # 핵심 결과 카드: EC별 평균 생중량 (필터링 적용)
        st.subheader(f"🥇 핵심 결과: {'전체 ' if selected_school == '전체' else selected_school + ' '}EC별 평균 생중량")
        
        avg_weights_by_ec = {}
        for school in filtered_schools:
            if school in growth_data:
                df = growth_data[school]
                if '생중량(g)' in df.columns:
                    ec = SCHOOL_INFO[school]['ec']
                    avg_weight = df['생중량(g)'].mean()
                    avg_weights_by_ec[f"EC {ec} ({school})"] = avg_weight
        
        if avg_weights_by_ec:
            # 동적 컬럼 생성
            num_schools = len(avg_weights_by_ec)
            cols = st.columns(num_schools)
            
            max_weight = max(avg_weights_by_ec.values())
            
            for idx, (label, weight) in enumerate(sorted(avg_weights_by_ec.items())):
                is_max = weight == max_weight
                cols[idx].metric(
                    label,
                    f"{weight:.3f}g",
                    delta="⭐ 최적" if is_max else None,
                    delta_color="normal" if is_max else "off"
                )
        
        # EC별 생육 비교 (필터링 적용)
        st.subheader(f"📊 {'전체 ' if selected_school == '전체' else selected_school + ' '}생육 비교")
        
        fig2 = make_subplots(
            rows=2, cols=2,
            subplot_titles=("⭐ 평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수 비교"),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # 필터링된 학교만 사용
        schools_list = [s for s in filtered_schools if s in growth_data]
        colors = [SCHOOL_INFO[s]["color"] for s in schools_list]
        
        # 평균 계산
        avg_weights = []
        avg_leaves = []
        avg_heights = []
        sample_counts = []
        
        for school in schools_list:
            df = growth_data[school]
            avg_weights.append(df['생중량(g)'].mean() if '생중량(g)' in df.columns else 0)
            avg_leaves.append(df['잎 수(장)'].mean() if '잎 수(장)' in df.columns else 0)
            avg_heights.append(df['지상부 길이(mm)'].mean() if '지상부 길이(mm)' in df.columns else 0)
            sample_counts.append(len(df))
        
        # 생중량
        fig2.add_trace(
            go.Bar(x=schools_list, y=avg_weights, marker_color=colors, showlegend=False),
            row=1, col=1
        )
        
        # 잎 수
        fig2.add_trace(
            go.Bar(x=schools_list, y=avg_leaves, marker_color=colors, showlegend=False),
            row=1, col=2
        )
        
        # 지상부 길이
        fig2.add_trace(
            go.Bar(x=schools_list, y=avg_heights, marker_color=colors, showlegend=False),
            row=2, col=1
        )
        
        # 개체수
        fig2.add_trace(
            go.Bar(x=schools_list, y=sample_counts, marker_color=colors, showlegend=False),
            row=2, col=2
        )
        
        fig2.update_xaxes(title_text="학교", row=2, col=1)
        fig2.update_xaxes(title_text="학교", row=2, col=2)
        fig2.update_yaxes(title_text="생중량 (g)", row=1, col=1)
        fig2.update_yaxes(title_text="잎 수 (장)", row=1, col=2)
        fig2.update_yaxes(title_text="길이 (mm)", row=2, col=1)
        fig2.update_yaxes(title_text="개체수", row=2, col=2)
        
        fig2.update_layout(
            height=600,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # 학교별 생중량 분포 (필터링 적용)
        st.subheader(f"📦 {'전체 ' if selected_school == '전체' else selected_school + ' '}생중량 분포")
        
        fig_box = go.Figure()
        for school in schools_list:
            df = growth_data[school]
            if '생중량(g)' in df.columns:
                fig_box.add_trace(go.Box(
                    y=df['생중량(g)'],
                    name=school,
                    marker_color=SCHOOL_INFO[school]['color']
                ))
        
        fig_box.update_layout(
            yaxis_title="생중량 (g)",
            height=400,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        
        st.plotly_chart(fig_box, use_container_width=True)
        
        # 상관관계 분석 (필터링 적용)
        st.subheader(f"🔗 {'전체 ' if selected_school == '전체' else selected_school + ' '}상관관계 분석")
        
        col1, col2 = st.columns(2)
        
        # 필터링된 데이터 합치기
        all_data = []
        for school in filtered_schools:
            if school in growth_data:
                df_copy = growth_data[school].copy()
                df_copy['학교'] = school
                df_copy['EC'] = SCHOOL_INFO[school]['ec']
                all_data.append(df_copy)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            with col1:
                if '잎 수(장)' in combined_df.columns and '생중량(g)' in combined_df.columns:
                    fig_corr1 = px.scatter(
                        combined_df,
                        x='잎 수(장)',
                        y='생중량(g)',
                        color='학교',
                        color_discrete_map={s: SCHOOL_INFO[s]['color'] for s in schools_list},
                        title="잎 수 vs 생중량"
                    )
                    fig_corr1.update_layout(
                        height=400,
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
                    )
                    st.plotly_chart(fig_corr1, use_container_width=True)
            
            with col2:
                if '지상부 길이(mm)' in combined_df.columns and '생중량(g)' in combined_df.columns:
                    fig_corr2 = px.scatter(
                        combined_df,
                        x='지상부 길이(mm)',
                        y='생중량(g)',
                        color='학교',
                        color_discrete_map={s: SCHOOL_INFO[s]['color'] for s in schools_list},
                        title="지상부 길이 vs 생중량"
                    )
                    fig_corr2.update_layout(
                        height=400,
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
                    )
                    st.plotly_chart(fig_corr2, use_container_width=True)
        
        # 생육 데이터 원본
        with st.expander("📋 생육 데이터 원본"):
            if selected_school == "전체":
                for school in filtered_schools:
                    if school in growth_data:
                        st.subheader(school)
                        st.dataframe(growth_data[school], use_container_width=True)
                
                # 전체 XLSX 다운로드
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    for school in filtered_schools:
                        if school in growth_data:
                            growth_data[school].to_excel(writer, sheet_name=school, index=False)
                buffer.seek(0)
                
                st.download_button(
                    label="📥 전체 생육 데이터 XLSX 다운로드",
                    data=buffer,
                    file_name="전체_생육결과데이터.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                if selected_school in growth_data:
                    st.dataframe(growth_data[selected_school], use_container_width=True)
                    
                    buffer = io.BytesIO()
                    growth_data[selected_school].to_excel(buffer, index=False, engine='openpyxl')
                    buffer.seek(0)
                    
                    st.download_button(
                        label=f"📥 {selected_school} XLSX 다운로드",
                        data=buffer,
                        file_name=f"{selected_school}_생육결과.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

if __name__ == "__main__":
    main()
