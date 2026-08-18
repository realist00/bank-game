# app.py - 학생 자율 회원가입/로그인 및 권한 분리 적용 버전

import streamlit as st
import pandas as pd
import math
import json
import os

# ==============================================================================
# 1. 페이지 기본 설정 및 디자인
# ==============================================================================
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

# ==============================================================================
# 2. 거시경제 시나리오 데이터 (11주차)
# ==============================================================================
SCENARIOS = {
    1: {
        "round_name": "Round 1 (2주차)", "phase": "영업 개시 및 시장 탐색기",
        "base_rate": 2.50, "gdp_growth": 2.5, "market_deposit_base": 10000.0, "market_loan_base": 8000.0,
        "gov_bond_yield": 2.70, "corp_bond_yield": 3.80, "base_npl_rate": 1.0,
        "news_headline": "📢 [금융 브리핑] 안정적인 경기 흐름 속 은행 영업 개시",
        "news_detail": "한국은행은 기준금리를 2.50%로 유지했습니다. 완만한 경기 성장세 속에서 각 은행은 초기 예대금리 전략을 수립해 고객 기반을 확보해야 합니다.",
        "instructor_tip": "예대마진(NIM)과 시장점유율의 상관관계를 확인하고, 극단적인 금리 경쟁의 위험성을 안내하세요."
    },
    2: {
        "round_name": "Round 2 (3주차)", "phase": "경기 호황 및 대출 수요 급증",
        "base_rate": 2.75, "gdp_growth": 3.8, "market_deposit_base": 11000.0, "market_loan_base": 9800.0,
        "gov_bond_yield": 2.95, "corp_bond_yield": 4.10, "base_npl_rate": 0.8,
        "news_headline": "📈 [산업 동향] 기업 설비투자 확대, 대출 수요 폭증!",
        "news_detail": "경기가 가파르게 성장하며 기업과 가계의 대출 수요가 급증했습니다. 외형 확장에 따른 자기자본비율(BIS) 관리에 유의해야 합니다.",
        "instructor_tip": "대출 확장이 단기 이익은 늘리지만 RWA 증가로 BIS비율을 떨어뜨릴 수 있음을 강조하세요."
    },
    3: {
        "round_name": "Round 3 (4주차)", "phase": "인플레이션 압박 및 금리 인상기",
        "base_rate": 3.75, "gdp_growth": 2.0, "market_deposit_base": 11200.0, "market_loan_base": 9200.0,
        "gov_bond_yield": 3.90, "corp_bond_yield": 5.20, "base_npl_rate": 1.2,
        "news_headline": "🔥 [통화 정책] 인플레이션 비상! 기준금리 1.00%p 전격 인상",
        "news_detail": "중앙은행이 빅스텝 금리 인상을 단행했습니다. 시중 예금 조달비용이 빠르게 증가하므로 ALM(금리 갭 리스크) 관리가 필수적입니다.",
        "instructor_tip": "단기 조달(예금) - 장기 운용(대출) 구조에서 금리 상승기가 조달비용에 미치는 충격을 설명하세요."
    },
    4: {
        "round_name": "Round 4 (5주차)", "phase": "고금리 지속 및 은행 간 예금 전쟁",
        "base_rate": 4.50, "gdp_growth": 1.2, "market_deposit_base": 11500.0, "market_loan_base": 8800.0,
        "gov_bond_yield": 4.60, "corp_bond_yield": 6.10, "base_npl_rate": 1.8,
        "news_headline": "⚔️ [금융권 경쟁] 유동성 흡수 심화, 시중은행 '고금리 특판' 출혈경쟁",
        "news_detail": "시중 유동성이 마르면서 은행 간 예금 유치 전쟁이 격화되고 있습니다. 금리를 낮추면 예금이 급격히 이탈하고, 높이면 마진이 급감합니다.",
        "instructor_tip": "마케팅비와 예금금리 조합을 통해 조달 유동성을 방어하는 전략을 유도하세요."
    },
    5: {
        "round_name": "Round 5 (6주차)", "phase": "경기 둔화 및 잠재 부실 누적",
        "base_rate": 4.50, "gdp_growth": 0.5, "market_deposit_base": 11300.0, "market_loan_base": 8200.0,
        "gov_bond_yield": 4.40, "corp_bond_yield": 6.50, "base_npl_rate": 2.5,
        "news_headline": "⚠️ [위험 징후] 고금리 장기화로 자영업자·중소기업 이자 부담 한계",
        "news_detail": "경기가 급격히 둔화되며 연체율이 상승하기 시작했습니다. 과거 무분별하게 대출 심사를 완화했던 은행들의 건전성에 빨간불이 켜졌습니다.",
        "instructor_tip": "대출 심사 기준(공격적 vs 보수적)의 누적 효과가 본격적으로 차이를 만들기 시작함을 보여주세요."
    },
    6: {
        "round_name": "Round 6 (7주차)", "phase": "[충격] 신용경색 및 부실 쇼크",
        "base_rate": 4.25, "gdp_growth": -0.8, "market_deposit_base": 10500.0, "market_loan_base": 7500.0,
        "gov_bond_yield": 4.00, "corp_bond_yield": 7.80, "base_npl_rate": 4.2,
        "news_headline": "💥 [금융 위기] 중견기업 연쇄 도산 및 부동산 PF 부실 쇼크!",
        "news_detail": "마이너스 성장에 진입하며 신용위기가 터졌습니다. 은행권 전반에 부실채권(NPL)이 폭증하고 대규모 충당금 전입으로 순이익이 급감합니다.",
        "instructor_tip": "BIS 비율 10.5% 방어가 최대 과제입니다. 충당금 전입과 자본 훼손을 어떻게 극복하는지 관찰하세요."
    },
    7: {
        "round_name": "Round 7 (8주차)", "phase": "감독당국의 규제 강화",
        "base_rate": 3.75, "gdp_growth": 0.2, "market_deposit_base": 10800.0, "market_loan_base": 7800.0,
        "gov_bond_yield": 3.60, "corp_bond_yield": 6.50, "base_npl_rate": 3.2,
        "news_headline": "📜 [규제 감독] 금융감독원, '은행 자본적정성 관리 강화 및 배당 자제 권고'",
        "news_detail": "감독당국이 부실 은행에 대한 경영개선 권고를 시작했습니다. 배당을 억제하고 이익을 사내 유보하여 자기자본비율을 정상화해야 합니다.",
        "instructor_tip": "위기 극복을 위한 디레버리징(자산 축소) 및 내부유보 중심의 자본 확충 전략을 피드백하세요."
    },
    8: {
        "round_name": "Round 8 (9주차)", "phase": "금리 인하 사이클 및 경기 회복기",
        "base_rate": 2.75, "gdp_growth": 1.8, "market_deposit_base": 11400.0, "market_loan_base": 8600.0,
        "gov_bond_yield": 2.90, "corp_bond_yield": 4.50, "base_npl_rate": 1.9,
        "news_headline": "🌱 [경기 회복] 한국은행 금리 전격 인하, 시장 정상화 시동",
        "news_detail": "기준금리가 인하되며 채권 가격이 상승(평가이익)하고 대출 수요가 회복됩니다. 건전성을 지켜낸 은행들이 재도약할 기회입니다.",
        "instructor_tip": "금리 하락기에 유가증권(국채/회사채) 포트폴리오가 창출하는 평가이익과 회복세를 확인하세요."
    },
    9: {
        "round_name": "Round 9 (10주차)", "phase": "최종 결산 라운드",
        "base_rate": 2.50, "gdp_growth": 2.2, "market_deposit_base": 12000.0, "market_loan_base": 9500.0,
        "gov_bond_yield": 2.65, "corp_bond_yield": 3.90, "base_npl_rate": 1.2,
        "news_headline": "🏁 [마지막 분기] 9개 분기 경영 대장정 마무리, 최종 주주가치 결정",
        "news_detail": "모든 시련을 거쳐 최종 결산에 도달했습니다. 최종 배당 정책과 포트폴리오 정리를 통해 최종 기업가치와 누적 ROE를 극대화하세요.",
        "instructor_tip": "최종 순위는 누적 ROE, 최종 주가, BIS 건전성을 종합 평가함을 상기시키세요."
    }
}

# ==============================================================================
# 3. 데이터 저장소 관리 (JSON)
# ==============================================================================
DATA_FILE = "bank_game_state.json"

def get_initial_bank_state(bank_id, bank_name):
    return {
        "round": 0, "bank_id": bank_id, "bank_name": bank_name,
        "cash_reserves": 175.0, "gov_bonds": 250.0, "corp_bonds": 125.0,
        "gross_loans": 2000.0, "allowance_losses": 10.0, "net_loans": 1990.0, "total_assets": 2540.0,
        "deposits": 2500.0, "borrowings": 0.0, "total_liabilities": 2500.0,
        "capital_stock": 200.0, "retained_earnings": 50.0, "total_equity": 250.0,
        "interest_income": 27.5, "interest_expense": 15.6, "net_interest_income": 11.9,
        "bond_valuation_gain": 0.0, "sga_expense": 4.5, "credit_loss_provision": 2.0,
        "pretax_income": 5.4, "tax_expense": 1.08, "net_income": 4.32, "dividend_paid": 0.86,
        "nim": 2.00, "bis_ratio": 12.12, "npl_ratio": 1.00, "roe": 7.00, "roa": 0.70,
        "stock_price": 10000.0, "cumulative_roe": 0.0, "deposit_share": 25.0, "loan_share": 25.0,
        "regulatory_status": "✅ 정상 (규제 통과)"
    }

def _load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return _init_default_data()
    return _init_default_data()

def _init_default_data():
    data = {
        "game_state": {"current_round": 1, "is_finished": False},
        "users": {},
        "teams": [],
        "decisions": {},
        "history": {}
    }
    _save_data(data)
    return data

def _save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==============================================================================
# 4. 시뮬레이션 계산 엔진
# ==============================================================================
def process_simulation_round(current_round, decisions_by_bank, previous_states_by_bank):
    scenario = SCENARIOS[current_round]
    prev_scenario = SCENARIOS.get(current_round - 1, {
        "gov_bond_yield": scenario["gov_bond_yield"], "corp_bond_yield": scenario["corp_bond_yield"]
    })
    
    bank_ids = list(decisions_by_bank.keys())
    if not bank_ids:
        return {}
    
    deposit_scores = {}
    loan_scores = {}
    for b_id in bank_ids:
        dec = decisions_by_bank[b_id]
        r_dep = float(dec.get("deposit_rate", scenario["base_rate"]))
        r_loan = float(dec.get("loan_rate", scenario["base_rate"] + 2.0))
        mkt_budget = float(dec.get("marketing_budget", 2.0))
        underwriting = dec.get("underwriting_standard", "표준")
        
        uw_loan_bonus = 0.25 if underwriting == "공격적" else (-0.25 if underwriting == "보수적" else 0.0)
        dep_score = math.exp(0.9 * (r_dep - scenario["base_rate"]) + 0.30 * math.log(max(0.5, mkt_budget)))
        loan_score = math.exp(-0.8 * (r_loan - (scenario["base_rate"] + 2.2)) + 0.30 * math.log(max(0.5, mkt_budget)) + uw_loan_bonus)
        deposit_scores[b_id] = dep_score
        loan_scores[b_id] = loan_score
        
    sum_dep = sum(deposit_scores.values())
    sum_loan = sum(loan_scores.values())
    deposit_shares = {b_id: deposit_scores[b_id] / sum_dep for b_id in bank_ids}
    loan_shares = {b_id: loan_scores[b_id] / sum_loan for b_id in bank_ids}
    
    new_states = {}
    for b_id in bank_ids:
        dec = decisions_by_bank[b_id]
        prev = previous_states_by_bank[b_id]
        
        r_dep = float(dec.get("deposit_rate", scenario["base_rate"]))
        r_loan = float(dec.get("loan_rate", scenario["base_rate"] + 2.0))
        mkt_budget = float(dec.get("marketing_budget", 2.0))
        underwriting = dec.get("underwriting_standard", "표준")
        bond_alloc_gov = float(dec.get("bond_allocation_gov", 70.0)) / 100.0
        payout_ratio = float(dec.get("dividend_payout_ratio", 20.0)) / 100.0
        
        scale = max(1.0, len(bank_ids) / 4.0)
        new_deposits = round(deposit_shares[b_id] * (scenario["market_deposit_base"] * scale), 1)
        new_loans = round(loan_shares[b_id] * (scenario["market_loan_base"] * scale), 1)
        required_reserves = round(new_deposits * 0.07, 1)
        
        funding_base = new_deposits + prev["total_equity"]
        operating_need = required_reserves + new_loans
        
        if funding_base >= operating_need:
            total_bonds = round(funding_base - operating_need, 1)
            new_gov_bonds = round(total_bonds * bond_alloc_gov, 1)
            new_corp_bonds = round(total_bonds * (1.0 - bond_alloc_gov), 1)
            new_borrowings = 0.0
        else:
            new_gov_bonds = 50.0
            new_corp_bonds = 30.0
            deficit = (operating_need + new_gov_bonds + new_corp_bonds) - funding_base
            new_borrowings = max(0.0, round(deficit, 1))
            
        uw_npl_mult = 1.6 if underwriting == "공격적" else (0.65 if underwriting == "보수적" else 1.0)
        spread_over_base = max(0.0, r_loan - (scenario["base_rate"] + 2.0))
        adverse_selection = spread_over_base * 0.15
        
        npl_rate = round(scenario["base_npl_rate"] * uw_npl_mult * (1.0 + adverse_selection), 2)
        credit_loss_provision = round(new_loans * (npl_rate / 100.0 / 4.0) * 0.8, 2)
        allowance_losses = round(prev.get("allowance_losses", 10.0) * 0.8 + credit_loss_provision, 1)
        net_loans = round(new_loans - allowance_losses, 1)
        
        int_inc_loan = new_loans * (r_loan / 100.0) / 4.0
        int_inc_gov = new_gov_bonds * (scenario["gov_bond_yield"] / 100.0) / 4.0
        int_inc_corp = new_corp_bonds * (scenario["corp_bond_yield"] / 100.0) / 4.0
        total_interest_income = round(int_inc_loan + int_inc_gov + int_inc_corp, 2)
        
        int_exp_dep = new_deposits * (r_dep / 100.0) / 4.0
        int_exp_borr = new_borrowings * ((scenario["base_rate"] + 2.0) / 100.0) / 4.0
        total_interest_expense = round(int_exp_dep + int_exp_borr, 2)
        net_interest_income = round(total_interest_income - total_interest_expense, 2)
        
        delta_gov = scenario["gov_bond_yield"] - prev_scenario["gov_bond_yield"]
        delta_corp = scenario["corp_bond_yield"] - prev_scenario["corp_bond_yield"]
        bond_gain_loss = round(new_gov_bonds * (-3.0 * delta_gov / 100.0) + new_corp_bonds * (-2.0 * delta_corp / 100.0), 2)
        
        sga_expense = round(2.0 + mkt_budget, 2)
        pretax_income = round(net_interest_income + bond_gain_loss - sga_expense - credit_loss_provision, 2)
        tax_expense = max(0.0, round(pretax_income * 0.20, 2)) if pretax_income > 0 else 0.0
        net_income = round(pretax_income - tax_expense, 2)
        
        dividend_paid = max(0.0, round(net_income * payout_ratio, 2)) if net_income > 0 else 0.0
        retained_added = round(net_income - dividend_paid, 2)
        new_retained_earnings = round(prev["retained_earnings"] + retained_added, 2)
        new_total_equity = round(prev["capital_stock"] + new_retained_earnings, 2)
        
        total_assets = round(required_reserves + new_gov_bonds + new_corp_bonds + net_loans, 1)
        total_liabilities = round(new_deposits + new_borrowings, 1)
        
        earning_assets = new_loans + new_gov_bonds + new_corp_bonds
        nim = round((net_interest_income * 4.0 / max(1.0, earning_assets)) * 100.0, 2)
        
        rwa = max(1.0, round(new_loans * 1.0 + new_corp_bonds * 0.5, 1))
        bis_ratio = round((new_total_equity / rwa) * 100.0, 2)
        
        roe = round((net_income * 4.0 / max(1.0, new_total_equity)) * 100.0, 2)
        roa = round((net_income * 4.0 / max(1.0, total_assets)) * 100.0, 2)
        cumulative_roe = round(prev.get("cumulative_roe", 0.0) + (roe / 4.0), 2)
        
        if bis_ratio < 8.0: regulatory_status = "🚨 경영개선명령 (영업정지 위기)"
        elif bis_ratio < 10.5: regulatory_status = "⚠️ 경영개선권고 (자본확충 필요)"
        else: regulatory_status = "✅ 정상 (규제 통과)"
            
        bps = (new_total_equity / 200.0) * 10000.0
        pbr_mult = max(0.4, min(2.0, 1.0 + (roe - 7.0) * 0.04 + (bis_ratio - 10.5) * 0.03))
        stock_price = max(1000.0, round(bps * pbr_mult, 0))
        
        new_states[b_id] = {
            "round": current_round, "bank_id": b_id, "bank_name": prev["bank_name"],
            "cash_reserves": required_reserves, "gov_bonds": new_gov_bonds, "corp_bonds": new_corp_bonds,
            "gross_loans": new_loans, "allowance_losses": allowance_losses, "net_loans": net_loans,
            "total_assets": total_assets, "deposits": new_deposits, "borrowings": new_borrowings,
            "total_liabilities": total_liabilities, "capital_stock": prev["capital_stock"],
            "retained_earnings": new_retained_earnings, "total_equity": new_total_equity,
            "interest_income": total_interest_income, "interest_expense": total_interest_expense,
            "net_interest_income": net_interest_income, "bond_valuation_gain": bond_gain_loss,
            "sga_expense": sga_expense, "credit_loss_provision": credit_loss_provision,
            "pretax_income": pretax_income, "tax_expense": tax_expense, "net_income": net_income,
            "dividend_paid": dividend_paid, "nim": nim, "bis_ratio": bis_ratio, "npl_ratio": npl_rate,
            "roe": roe, "roa": roa, "cumulative_roe": cumulative_roe, "stock_price": stock_price,
            "deposit_share": round(deposit_shares[b_id] * 100.0, 1), "loan_share": round(loan_shares[b_id] * 100.0, 1),
            "regulatory_status": regulatory_status
        }
    return new_states

# ==============================================================================
# 5. 세션 상태 및 화면 분기
# ==============================================================================
data = _load_data()
game_state = data.get("game_state", {"current_round": 1, "is_finished": False})
curr_round = game_state["current_round"]
is_finished = game_state["is_finished"]

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

st.sidebar.markdown("### 🏦 상업은행 경영 시뮬레이션")
st.sidebar.markdown(f"**진행 현황:** {'🏁 결산 완료' if is_finished else f'📍 Round {curr_round} / 9 (총 11주차)'}")

if curr_round in SCENARIOS:
    sc = SCENARIOS[curr_round]
    st.sidebar.info(f"**기준금리:** {sc['base_rate']:.2f}%\n\n**성장률:** {sc['gdp_growth']:+.1f}%\n\n**단계:** {sc['phase']}")

if st.session_state.auth_user is not None:
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
        st.session_state.auth_user = None
        st.rerun()

# -------------------------------------------------------------
# [1] 비로그인 상태 (가입 / 로그인 / 관리자접속)
# -------------------------------------------------------------
if st.session_state.auth_user is None:
    st.markdown("<div class='main-title'>🏦 상업은행 경영 시뮬레이션 시스템</div>", unsafe_allow_html=True)
    st.caption("수업에 참여하는 학생은 이메일로 가입/로그인하시고, 교수님은 관리자 탭에서 로그인하세요.")
    
    login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 학생 로그인", "📝 학생 신규 회원가입", "👨‍🏫 교수자(관리자) 접속"])
    
    with login_tab1:
        st.markdown("#### 학생 로그인")
        with st.form("student_login_form"):
            login_email = st.text_input("이메일 주소", placeholder="student@hannam.ac.kr")
            login_pw = st.text_input("비밀번호", type="password")
            btn_login = st.form_submit_button("로그인", use_container_width=True)
            
            if btn_login:
                users = data.get("users", {})
                if login_email in users and users[login_email]["password"] == login_pw:
                    u_info = users[login_email]
                    st.session_state.auth_user = {
                        "role": "student",
                        "email": login_email,
                        "bank_id": u_info["bank_id"],
                        "bank_name": u_info["bank_name"]
                    }
                    st.success(f"반갑습니다! **{u_info['bank_name']}**으로 로그인되었습니다.")
                    st.rerun()
                else:
                    st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
                    
    with login_tab2:
        st.markdown("#### 학생 신규 팀(은행) 등록")
        st.caption("이메일과 비밀번호를 등록하고, 우리 팀만의 은행 이름을 직접 지어주세요!")
        with st.form("student_signup_form"):
            reg_email = st.text_input("이메일 주소 (아이디로 사용)", placeholder="student1@hannam.ac.kr")
            reg_pw = st.text_input("비밀번호 설정", type="password")
            reg_bank_name = st.text_input("우리 팀 은행 이름 (예: 한남혁신은행, 블루오션뱅크 등)", placeholder="OO은행")
            btn_signup = st.form_submit_button("가입 및 은행 설립하기", use_container_width=True)
            
            if btn_signup:
                if not reg_email or not reg_pw or not reg_bank_name:
                    st.warning("이메일, 비밀번호, 은행 이름을 모두 입력해 주세요.")
                elif reg_email in data.get("users", {}):
                    st.error("이미 가입된 이메일 주소입니다. 로그인을 이용해 주세요.")
                else:
                    new_bank_id = f"bank_{len(data.get('teams', [])) + 1}_{abs(hash(reg_email)) % 10000}"
                    data["users"][reg_email] = {
                        "password": reg_pw,
                        "bank_id": new_bank_id,
                        "bank_name": reg_bank_name
                    }
                    data["teams"].append({
                        "bank_id": new_bank_id,
                        "bank_name": reg_bank_name,
                        "email": reg_email
                    })
                    init_st = get_initial_bank_state(new_bank_id, reg_bank_name)
                    data["history"][new_bank_id] = [init_st]
                    _save_data(data)
                    st.success(f"🎉 **{reg_bank_name}**이(가) 성공적으로 설립되었습니다! [학생 로그인] 탭에서 로그인해 주세요.")
                    
    with login_tab3:
        st.markdown("#### 교수자 관리자 로그인")
        with st.form("admin_login_form"):
            admin_pw_input = st.text_input("관리자 마스터 비밀번호", type="password", placeholder="비밀번호 입력")
            btn_admin_login = st.form_submit_button("관리자 접속", use_container_width=True)
            if btn_admin_login:
                if admin_pw_input == "admin1234":
                    st.session_state.auth_user = {"role": "admin"}
                    st.success("교수자 관리자 모드로 접속되었습니다.")
                    st.rerun()
                else:
                    st.error("관리자 비밀번호가 올바르지 않습니다. (기본: admin1234)")

# -------------------------------------------------------------
# [2] 학생 전용 대시보드 (학생 로그인 시)
# -------------------------------------------------------------
elif st.session_state.auth_user.get("role") == "student":
    user_info = st.session_state.auth_user
    my_bank_id = user_info["bank_id"]
    my_bank_name = user_info["bank_name"]
    
    st.markdown(f"<div class='main-title'>🏛️ {my_bank_name} 경영본부</div>", unsafe_allow_html=True)
    st.caption(f"접속 계정: `{user_info['email']}`")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📢 시장 브리핑 & 경제 시나리오", "✍️ 의사결정 제출", "📊 우리 은행 재무제표", "🏆 시장 전체 순위"])
    
    with tab1:
        if is_finished:
            st.success("🎉 모든 9개 라운드가 종료되었습니다! 최종 경영 성과를 확인하세요.")
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
            st.warning("게임이 종료되어 의사결정이 마감되었습니다.")
        else:
            sc = SCENARIOS[curr_round]
            st.markdown(f"#### 📝 Round {curr_round} 경영 의사결정 입력")
            prev_dec = data.get("decisions", {}).get(f"round_{curr_round}", {}).get(my_bank_id, {})
            
            with st.form("student_decision_form"):
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
                    r_key = f"round_{curr_round}"
                    if r_key not in data["decisions"]: data["decisions"][r_key] = {}
                    data["decisions"][r_key][my_bank_id] = dec_dict
                    _save_data(data)
                    st.success("✅ 의사결정이 정상 제출되었습니다!")

    with tab3:
        history = data.get("history", {}).get(my_bank_id, [])
        if history:
            latest = history[-1]
            st.markdown(f"#### 📊 {my_bank_name} 경영 성과 리포트 (직전 결산: Round {latest['round']})")
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
                
            if len(history) > 1:
                st.markdown("##### 📉 라운드별 주요 경영 지표 추이")
                hist_df = pd.DataFrame(history).set_index("round")
                c_ch1, c_ch2 = st.columns(2)
                with c_ch1:
                    st.markdown("**주가 추이 (원)**")
                    st.line_chart(hist_df[["stock_price"]])
                with c_ch2:
                    st.markdown("**BIS 자기자본비율 추이 (%)**")
                    st.line_chart(hist_df[["bis_ratio"]])

    with tab4:
        st.markdown("#### 🏆 전체 은행 경쟁 현황")
        summary_list = []
        for t in data.get("teams", []):
            t_hist = data.get("history", {}).get(t["bank_id"], [])
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

# -------------------------------------------------------------
# [3] 교수자 전용 관리자 대시보드 (관리자 로그인 시)
# -------------------------------------------------------------
elif st.session_state.auth_user.get("role") == "admin":
    st.markdown("<div class='main-title'>👨‍🏫 교수자 전용 관리자 대시보드</div>", unsafe_allow_html=True)
    
    adm_tab1, adm_tab2, adm_tab3 = st.tabs(["🕹️ 라운드 진행 및 결산", "📈 전체 성과 종합 비교", "⚙️ 참여 은행 관리 및 초기화"])
    
    with adm_tab1:
        st.markdown(f"### 📍 현재 진행 단계: **Round {curr_round} / 9**")
        if is_finished:
            st.success("🏁 9라운드 시뮬레이션이 모두 마감되었습니다.")
        else:
            sc = SCENARIOS.get(curr_round, {})
            st.info(f"**이번 라운드 시나리오:** {sc.get('news_headline', '')}\n\n💡 **교수자 가이드 팁:** {sc.get('instructor_tip', '')}")
            
            decisions_curr = data.get("decisions", {}).get(f"round_{curr_round}", {})
            teams_list = data.get("teams", [])
            
            st.markdown(f"#### 📋 등록된 학생 은행 ({len(teams_list)}개) 제출 현황")
            if not teams_list:
                st.warning("아직 학생들이 가입하여 설립한 은행이 없습니다.")
            else:
                status_data = []
                for t in teams_list:
                    b_id = t["bank_id"]
                    submitted = b_id in decisions_curr
                    dec = decisions_curr.get(b_id, {})
                    status_data.append({
                        "은행명": t["bank_name"],
                        "소유자(이메일)": t.get("email", "-"),
                        "제출 상태": "✅ 제출 완료" if submitted else "⏳ 미제출 (기본값 대기)",
                        "예금금리": f"{dec.get('deposit_rate', '-')}%",
                        "대출금리": f"{dec.get('loan_rate', '-')}%",
                        "심사강도": dec.get('underwriting_standard', '-'),
                        "마케팅비": f"{dec.get('marketing_budget', '-')}억"
                    })
                st.table(pd.DataFrame(status_data))
                
                if st.button(f"🚨 [Round {curr_round} 결산 실행 및 Round {curr_round+1} 시작]", type="primary", use_container_width=True):
                    r_key = f"round_{curr_round}"
                    decisions = data.get("decisions", {}).get(r_key, {})
                    prev_states = {}
                    for t in teams_list:
                        b_id = t["bank_id"]
                        hist = data["history"].get(b_id, [])
                        prev_states[b_id] = hist[-1] if hist else get_initial_bank_state(b_id, t["bank_name"])
                        if b_id not in decisions:
                            sc_curr = SCENARIOS[curr_round]
                            decisions[b_id] = {
                                "deposit_rate": sc_curr["base_rate"], "loan_rate": sc_curr["base_rate"] + 2.0,
                                "marketing_budget": 2.0, "underwriting_standard": "표준",
                                "bond_allocation_gov": 70.0, "dividend_payout_ratio": 20.0
                            }
                            if r_key not in data["decisions"]: data["decisions"][r_key] = {}
                            data["decisions"][r_key][b_id] = decisions[b_id]
                    new_states = process_simulation_round(curr_round, decisions, prev_states)
                    for b_id, s in new_states.items():
                        data["history"][b_id].append(s)
                    next_round = curr_round + 1
                    data["game_state"]["current_round"] = next_round
                    data["game_state"]["is_finished"] = True if next_round > 9 else False
                    _save_data(data)
                    st.success(f"🎉 Round {curr_round} 결산 완료! (현재: Round {next_round})")
                    st.rerun()

    with adm_tab2:
        st.markdown("### 📊 팀별 경영 성과 비교 대시보드")
        teams_list = data.get("teams", [])
        all_histories = [record for t in teams_list for record in data.get("history", {}).get(t["bank_id"], [])]
        if all_histories and len(all_histories) > len(teams_list):
            df_all = pd.DataFrame(all_histories)
            
            df_pivot_stock = df_all.pivot(index="round", columns="bank_name", values="stock_price")
            df_pivot_bis = df_all.pivot(index="round", columns="bank_name", values="bis_ratio")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### 📈 팀별 주가 추이 (원)")
                st.line_chart(df_pivot_stock)
            with c2:
                st.markdown("##### 🛡️ 팀별 BIS 자기자본비율 추이 (%)")
                st.line_chart(df_pivot_bis)
                
            csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 결산 데이터 다운로드 (CSV)", csv_data, "bank_game_results.csv", "text/csv", use_container_width=True)
        else:
            st.info("라운드 결산이 진행되면 전체 팀 비교 차트가 활성화됩니다.")

    with adm_tab3:
        st.markdown("### ⚙️ 게임 관리 및 초기화")
        st.caption("새로운 학기나 테스트를 위해 등록된 학생 계정 및 게임 기록을 초기화할 수 있습니다.")
        if st.button("⚠️ [주의] 게임 전체 데이터 및 등록 계정 초기화"):
            _init_default_data()
            st.warning("초기화가 완료되었습니다. 학생들이 새롭게 가입할 수 있습니다.")
            st.rerun()
