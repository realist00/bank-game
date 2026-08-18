# app.py - 스탠포드 뱅킹 게임 웹 애플리케이션 (Streamlit)

import streamlit as st
import pandas as pd
import plotly.express as px
import database
from scenarios import SCENARIOS

st.set_page_config(
    page_title="스탠포드 뱅킹 게임 (Stanford Bank Game)",
    page_icon="🏦",
    layout="wide"
)

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0.2rem; }
    .highlight-news { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

game_state = database.get_game_state()
curr_round = game_state["current_round"]
is_finished = game_state["is_finished"]
teams = database.get_all_teams()

st.sidebar.markdown("### 🏦 상업은행 경영 시뮬레이션")
st.sidebar.markdown(f"**진행 상황:** {'🏁 최종 결산 완료' if is_finished else f'📍 Round {curr_round} / 9 (총 11주차)'}")

if curr_round in SCENARIOS:
    sc = SCENARIOS[curr_round]
    st.sidebar.info(f"**기준금리:** {sc['base_rate']:.2f}%\n\n**경제성장률:** {sc['gdp_growth']:+.1f}%\n\n**단계:** {sc['phase']}")

role = st.sidebar.radio("접속 모드 선택", ["👨‍🎓 학생용 화면", "👨‍🏫 교수자(관리자) 화면"])

# 1. 학생용 화면
if role == "👨‍🎓 학생용 화면":
    st.markdown("<div class='main-title'>🏦 상업은행 경영 시뮬레이션 (학생 포털)</div>", unsafe_allow_html=True)
    
    team_options = {t["bank_id"]: t["bank_name"] for t in teams}
    selected_team_id = st.sidebar.selectbox("우리 팀(은행) 선택", list(team_options.keys()), format_func=lambda x: team_options[x])
    my_team_name = team_options[selected_team_id]
    
    st.markdown(f"### 🚩 **{my_team_name}** 경영본부")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📢 시장 브리핑 & 경제 시나리오", "✍️ 의사결정 제출", "📊 재무제표 및 경영성과", "🏆 시장 전체 순위"])
    
    with tab1:
        if is_finished:
            st.success("🎉 모든 9개 라운드가 종료되었습니다! 최종 결과를 확인하세요.")
        else:
            sc = SCENARIOS[curr_round]
            st.markdown(f"#### 📅 {sc['round_name']} : {sc['phase']}")
            st.markdown(f"""
            <div class='highlight-news'>
                <h3>{sc['news_headline']}</h3>
                <p style='font-size: 1.05rem; line-height: 1.6;'>{sc['news_detail']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("한국은행 기준금리", f"{sc['base_rate']:.2f}%")
            c2.metric("실질 GDP 성장률", f"{sc['gdp_growth']:+.1f}%")
            c3.metric("국채 수익률", f"{sc['gov_bond_yield']:.2f}%")
            c4.metric("회사채 수익률", f"{sc['corp_bond_yield']:.2f}%")

    with tab2:
        if is_finished:
            st.warning("게임이 종료되었습니다.")
        else:
            sc = SCENARIOS[curr_round]
            st.markdown(f"#### 📝 Round {curr_round} 경영 의사결정 입력")
            prev_dec = database.get_team_decision(curr_round, selected_team_id) or {}
            
            with st.form("decision_form"):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown("##### 1. 자금 조달 & 대출 정책")
                    dep_rate = st.slider("1) 정기예금 금리 (%)", 0.5, 8.0, float(prev_dec.get("deposit_rate", sc["base_rate"])), 0.1)
                    loan_rate = st.slider("2) 일반대출 금리 (%)", 1.0, 15.0, float(prev_dec.get("loan_rate", sc["base_rate"] + 2.2)), 0.1)
                    uw_options = ["보수적 (엄격 심사)", "표준 (적정 심사)", "공격적 (완화 심사)"]
                    uw_idx = 0 if "보수" in prev_dec.get("underwriting_standard", "") else (2 if "공격" in prev_dec.get("underwriting_standard", "") else 1)
                    underwriting = st.selectbox("3) 대출 심사 강도", uw_options, index=uw_idx)
                    
                with col_d2:
                    st.markdown("##### 2. 마케팅 & 자산배분 & 자본정책")
                    mkt_budget = st.slider("4) 영업 및 마케팅 예산 (억원)", 0.5, 10.0, float(prev_dec.get("marketing_budget", 2.0)), 0.5)
                    bond_gov = st.slider("5) 잉여 유가증권 중 국채 투자 비중 (%)", 0.0, 100.0, float(prev_dec.get("bond_allocation_gov", 70.0)), 5.0)
                    dividend_payout = st.slider("6) 배당 성향 (%)", 0.0, 100.0, float(prev_dec.get("dividend_payout_ratio", 20.0)), 5.0)
                
                spread = loan_rate - dep_rate
                st.markdown("---")
                if spread < 0.5:
                    st.warning(f"⚠️ 경고: 예대금리차(Spread)가 `{spread:.2f}%p`로 너무 좁아 적자 위험이 있습니다!")
                else:
                    st.info(f"💡 현재 설정된 예대금리차: `{spread:.2f}%p` (대출 {loan_rate:.1f}% - 예금 {dep_rate:.1f}%)")
                    
                if st.form_submit_button("💾 의사결정 저장 및 제출하기", use_container_width=True):
                    clean_uw = "보수적" if "보수" in underwriting else ("공격적" if "공격" in underwriting else "표준")
                    dec_dict = {
                        "deposit_rate": dep_rate, "loan_rate": loan_rate,
                        "underwriting_standard": clean_uw, "marketing_budget": mkt_budget,
                        "bond_allocation_gov": bond_gov, "dividend_payout_ratio": dividend_payout
                    }
                    database.save_team_decision(curr_round, selected_team_id, dec_dict)
                    st.success("✅ 의사결정이 정상 제출되었습니다!")

    with tab3:
        history = database.get_bank_history(selected_team_id)
        if history:
            latest = history[-1]
            st.markdown(f"#### 📊 {my_team_name} 경영 성과 (직전 결산: Round {latest['round']})")
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("주가", f"{latest.get('stock_price', 10000):,.0f} 원")
            k2.metric("BIS 자기자본비율", f"{latest.get('bis_ratio', 12.0):.2f}%")
            k3.metric("순이자마진 (NIM)", f"{latest.get('nim', 2.0):.2f}%")
            k4.metric("당기순이익", f"{latest.get('net_income', 0.0):.2f} 억")
            k5.metric("ROE", f"{latest.get('roe', 0.0):.2f}%")
            k6.metric("부실채권비율 (NPL)", f"{latest.get('npl_ratio', 1.0):.2f}%")
            st.markdown(f"**규제 상태:** {latest.get('regulatory_status', '정상')}")
            st.markdown("---")
            
            c_bs, c_pl = st.columns(2)
            with c_bs:
                st.markdown("##### 🏛️ 재무상태표 (BS) - 단위: 억원")
                st.table(pd.DataFrame({
                    "항목": ["현금 및 지급준비금", "국채", "회사채", "총대출금", "(대손충당금)", "순대출금", "자산 총계", "총예금", "콜차입금", "부채 총계", "납입자본금", "이익잉여금", "자본 총계"],
                    "금액": [latest.get("cash_reserves", 0), latest.get("gov_bonds", 0), latest.get("corp_bonds", 0), latest.get("gross_loans", 0), f"-{latest.get('allowance_losses', 0)}", latest.get("net_loans", 0), latest.get("total_assets", 0), latest.get("deposits", 0), latest.get("borrowings", 0), latest.get("total_liabilities", 0), latest.get("capital_stock", 0), latest.get("retained_earnings", 0), latest.get("total_equity", 0)]
                }))
            with c_pl:
                st.markdown("##### 📈 손익계산서 (PL) - 단위: 억원")
                st.table(pd.DataFrame({
                    "항목": ["이자수익", "이자비용", "순이자이익 (NII)", "유가증권 평가손익", "판매비와관리비", "대손충당금 전입액", "세전순이익", "법인세비용", "당기순이익", "배당금 지급액"],
                    "금액": [latest.get("interest_income", 0), latest.get("interest_expense", 0), latest.get("net_interest_income", 0), latest.get("bond_valuation_gain", 0), latest.get("sga_expense", 0), latest.get("credit_loss_provision", 0), latest.get("pretax_income", 0), latest.get("tax_expense", 0), latest.get("net_income", 0), latest.get("dividend_paid", 0)]
                }))

    with tab4:
        st.markdown("#### 🏆 전체 은행 경쟁 현황")
        summary_list = []
        for t in teams:
            t_hist = database.get_bank_history(t["bank_id"])
            if t_hist:
                last_s = t_hist[-1]
                summary_list.append({
                    "은행명": last_s["bank_name"],
                    "주가 (원)": last_s.get("stock_price", 10000),
                    "누적 ROE (%)": last_s.get("cumulative_roe", 0.0),
                    "BIS 비율 (%)": last_s.get("bis_ratio", 12.0),
                    "총자산 (억원)": last_s.get("total_assets", 0),
                    "예금점유율 (%)": last_s.get("deposit_share", 0),
                    "대출점유율 (%)": last_s.get("loan_share", 0),
                    "규제 상태": last_s.get("regulatory_status", "정상")
                })
        if summary_list:
            df_sum = pd.DataFrame(summary_list).sort_values(by="주가 (원)", ascending=False).reset_index(drop=True)
            df_sum.index = df_sum.index + 1
            st.dataframe(df_sum, use_container_width=True)

# 2. 교수자 관리자 화면
else:
    st.markdown("<div class='main-title'>👨‍🏫 교수자 전용 관리자 대시보드</div>", unsafe_allow_html=True)
    admin_pw = st.sidebar.text_input("관리자 비밀번호 입력", type="password", value="admin1234")
    if admin_pw != "admin1234":
        st.error("비밀번호가 올바르지 않습니다. (기본: admin1234)")
        st.stop()
        
    adm_tab1, adm_tab2, adm_tab3 = st.tabs(["🕹️ 라운드 진행 및 결산", "📈 전체 성과 종합 비교", "⚙️ 게임 환경 설정"])
    
    with adm_tab1:
        st.markdown(f"### 📍 현재 진행 단계: **Round {curr_round} / 9**")
        if is_finished:
            st.success("🏁 9라운드 시뮬레이션이 모두 마감되었습니다.")
        else:
            sc = SCENARIOS.get(curr_round, {})
            st.info(f"**이번 라운드 시나리오:** {sc.get('news_headline', '')}\n\n💡 **교수자 가이드 팁:** {sc.get('instructor_tip', '')}")
            
            decisions_curr = database.get_all_decisions_for_round(curr_round)
            status_data = []
            for t in teams:
                b_id = t["bank_id"]
                submitted = b_id in decisions_curr
                dec = decisions_curr.get(b_id, {})
                status_data.append({
                    "팀 ID": b_id, "은행명": t["bank_name"],
                    "제출 상태": "✅ 제출 완료" if submitted else "⏳ 미제출 (기본값 대기)",
                    "예금금리": f"{dec.get('deposit_rate', '-')}%", "대출금리": f"{dec.get('loan_rate', '-')}%",
                    "심사강도": dec.get('underwriting_standard', '-'), "마케팅비": f"{dec.get('marketing_budget', '-')}억"
                })
            st.table(pd.DataFrame(status_data))
            
            if st.button(f"🚨 [Round {curr_round} 결산 실행 및 Round {curr_round+1} 시작]", type="primary", use_container_width=True):
                next_r, fin = database.advance_round()
                st.success(f"🎉 Round {curr_round} 결산 완료! (현재: Round {next_r})")
                st.rerun()

    with adm_tab2:
        st.markdown("### 📊 팀별 경영 성과 비교 대시보드")
        all_histories = [record for t in teams for record in database.get_bank_history(t["bank_id"])]
        if all_histories:
            df_all = pd.DataFrame(all_histories)
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.line(df_all, x="round", y="stock_price", color="bank_name", markers=True, title="팀별 주가 추이 (원)"), use_container_width=True)
            with c2:
                fig_bis = px.line(df_all, x="round", y="bis_ratio", color="bank_name", markers=True, title="팀별 BIS 비율 추이 (%)")
                fig_bis.add_hline(y=10.5, line_dash="dash", line_color="red", annotation_text="최저 규제선 (10.5%)")
                st.plotly_chart(fig_bis, use_container_width=True)
                
            csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 결산 데이터 다운로드 (CSV)", csv_data, "bank_game_results.csv", "text/csv", use_container_width=True)

    with adm_tab3:
        st.markdown("### ⚙️ 게임 관리 및 초기화")
        num_teams_sel = st.selectbox("참여 팀 수 선택", [4, 5, 6, 8], index=0)
        if st.button("⚠️ [주의] 게임 전체 데이터 초기화"):
            database.reset_game(num_teams_sel)
            st.warning("초기화 완료! Round 1부터 시작합니다.")
            st.rerun()