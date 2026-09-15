# app.py - 경기선행지표 순수 수치화(학생 자기주도 학습용) 및 세션 유지, 교수자 재무제표 종합 열람 완성본

import streamlit as st
import pandas as pd
import math
import json
import os
import requests

# ==============================================================================
# 1. 페이지 기본 설정 및 디자인
# ==============================================================================
st.set_page_config(
    page_title="상업은행 경영게임 (Banking Game)",
    page_icon="🏦",
    layout="wide"
)

DEFAULT_GSHEETS_URL = "https://script.google.com/macros/s/AKfycbx9_Z0QbBcNPNosboMfKl3p2MixjlypKVDG0S41C1qmwaM4h7H055zCsSchDVYQ9xDB/exec"

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0.2rem; }
    .highlight-news { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px; margin-bottom: 15px; }
    .team-badge { background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 8px 14px; border-radius: 6px; font-size: 0.95rem; color: #334155; margin-bottom: 15px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

def fmt_num(val):
    if isinstance(val, (int, float)):
        return f"{val:,.2f}"
    try:
        s = str(val).strip()
        is_neg = s.startswith("-")
        clean_s = s.replace(",", "").replace("-", "")
        f_val = float(clean_s)
        return f"-{f_val:,.2f}" if is_neg else f"{f_val:,.2f}"
    except Exception:
        return str(val)

def render_financial_html_table(title, items, amounts):
    rows = ""
    for item, amt in zip(items, amounts):
        is_total = any(k in item for k in ["총계", "당기순이익", "순이자이익", "순대출금"])
        row_style = "font-weight: 700; background-color: #F8FAFC; border-top: 1px solid #CBD5E1; border-bottom: 1px solid #CBD5E1; color: #0F172A;" if is_total else "border-bottom: 1px solid #F1F5F9; color: #334155;"
        amt_str = fmt_num(amt)
        rows += f'<tr style="{row_style}"><td style="text-align: left; padding: 9px 16px;">{item}</td><td style="text-align: right; padding: 9px 16px; font-family: \'Consolas\', \'Courier New\', monospace; font-size: 0.98rem;">{amt_str}</td></tr>'
    
    html = f'<div style="background-color: white; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><div style="background-color: #F8FAFC; padding: 12px 16px; font-weight: 700; border-bottom: 1px solid #E2E8F0; color: #1E3A8A; font-size: 1.05rem;">{title}</div><table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;"><thead><tr style="background-color: #F1F5F9; border-bottom: 2px solid #CBD5E1; color: #475569;"><th style="text-align: left; padding: 9px 16px; width: 60%;">항목</th><th style="text-align: right; padding: 9px 16px; width: 40%;">금액 (억원)</th></tr></thead><tbody>{rows}</tbody></table></div>'
    return html

def set_login_params(role, email=None):
    try:
        if role == "student" and email:
            st.query_params["user"] = email
            if "admin" in st.query_params:
                del st.query_params["admin"]
        elif role == "admin":
            st.query_params["admin"] = "1"
            if "user" in st.query_params:
                del st.query_params["user"]
    except Exception:
        pass

def clear_login_params():
    try:
        st.query_params.clear()
    except Exception:
        pass

def get_login_params():
    try:
        user = st.query_params.get("user")
        admin = st.query_params.get("admin")
        return user, admin
    except Exception:
        return None, None

# ==============================================================================
# 2. 11주차 거시경제 시나리오 및 순수 수치형 경기선행지표
# ==============================================================================
SCENARIOS = {
    1: {
        "round_name": "Round 1 (2주차)", "phase": "영업 개시 및 시장 탐색기",
        "base_rate": 2.50, "gdp_growth": 2.5, "market_deposit_base": 10000.0, "market_loan_base": 8000.0,
        "gov_bond_yield": 2.70, "corp_bond_yield": 3.80, "base_npl_rate": 1.0,
        "news_headline": "📢 [금융 브리핑] 안정적인 경기 흐름 속 은행 영업 개시",
        "news_detail": "한국은행은 기준금리를 2.50%로 유지했습니다. 완만한 경기 성장세 속에서 각 은행은 초기 예대금리 전략을 수립해 고객 기반을 확보해야 합니다.",
        "instructor_tip": "예대마진(NIM)과 시장점유율의 상관관계를 확인하고, 극단적인 금리 경쟁의 위험성을 안내하세요.",
        "leading": {
            "cli": "101.5",
            "yield_curve": "+0.85%p",
            "credit_spread": "1.10%p"
        }
    },
    2: {
        "round_name": "Round 2 (3주차)", "phase": "경기 호황 및 대출 수요 급증",
        "base_rate": 2.75, "gdp_growth": 3.8, "market_deposit_base": 11000.0, "market_loan_base": 9800.0,
        "gov_bond_yield": 2.95, "corp_bond_yield": 4.10, "base_npl_rate": 0.8,
        "news_headline": "📈 [산업 동향] 기업 설비투자 확대, 대출 수요 폭증!",
        "news_detail": "경기가 가파르게 성장하며 기업과 가계의 대출 수요가 급증했습니다. 외형 확장에 따른 자기자본비율(BIS) 관리에 유의해야 합니다.",
        "instructor_tip": "대출 확장이 단기 이익은 늘리지만 RWA 증가로 BIS비율을 떨어뜨릴 수 있음을 강조하세요.",
        "leading": {
            "cli": "102.8",
            "yield_curve": "+0.25%p",
            "credit_spread": "1.20%p"
        }
    },
    3: {
        "round_name": "Round 3 (4주차)", "phase": "인플레이션 압박 및 금리 인상기",
        "base_rate": 3.75, "gdp_growth": 2.0, "market_deposit_base": 11200.0, "market_loan_base": 9200.0,
        "gov_bond_yield": 3.90, "corp_bond_yield": 5.20, "base_npl_rate": 1.2,
        "news_headline": "🔥 [통화 정책] 인플레이션 비상! 기준금리 1.00%p 전격 인상",
        "news_detail": "중앙은행이 빅스텝 금리 인상을 단행했습니다. 시중 예금 조달비용이 빠르게 증가하므로 ALM(금리 갭 리스크) 관리가 필수적입니다.",
        "instructor_tip": "단기 조달(예금) - 장기 운용(대출) 구조에서 금리 상승기가 조달비용에 미치는 충격을 설명하세요.",
        "leading": {
            "cli": "101.0",
            "yield_curve": "-0.10%p",
            "credit_spread": "1.50%p"
        }
    },
    4: {
        "round_name": "Round 4 (5주차)", "phase": "고금리 지속 및 은행 간 예금 전쟁",
        "base_rate": 4.50, "gdp_growth": 1.2, "market_deposit_base": 11500.0, "market_loan_base": 8800.0,
        "gov_bond_yield": 4.60, "corp_bond_yield": 6.10, "base_npl_rate": 1.8,
        "news_headline": "⚔️ [금융권 경쟁] 유동성 흡수 심화, 시중은행 '고금리 특판' 출혈경쟁",
        "news_detail": "시중 유동성이 마르면서 은행 간 예금 유치 전쟁이 격화되고 있습니다. 금리를 낮추면 예금이 급격히 이탈하고, 높이면 마진이 급감합니다.",
        "instructor_tip": "마케팅비와 예금금리 조합을 통해 조달 유동성을 방어하는 전략을 유도하세요.",
        "leading": {
            "cli": "99.2",
            "yield_curve": "-0.30%p",
            "credit_spread": "2.10%p"
        }
    },
    5: {
        "round_name": "Round 5 (6주차)", "phase": "경기 둔화 및 잠재 부실 누적",
        "base_rate": 4.50, "gdp_growth": 0.5, "market_deposit_base": 11300.0, "market_loan_base": 8200.0,
        "gov_bond_yield": 4.40, "corp_bond_yield": 6.50, "base_npl_rate": 2.5,
        "news_headline": "⚠️ [위험 징후] 고금리 장기화로 자영업자·중소기업 이자 부담 한계",
        "news_detail": "경기가 급격히 둔화되며 연체율이 상승하기 시작했습니다. 과거 무분별하게 대출 심사를 완화했던 은행들의 건전성에 빨간불이 켜졌습니다.",
        "instructor_tip": "대출 심사 기준(공격적 vs 보수적)의 누적 효과가 본격적으로 차이를 만들기 시작함을 보여주세요.",
        "leading": {
            "cli": "97.5",
            "yield_curve": "-0.50%p",
            "credit_spread": "3.80%p"
        }
    },
    6: {
        "round_name": "Round 6 (7주차)", "phase": "[충격] 신용경색 및 부실 쇼크",
        "base_rate": 4.25, "gdp_growth": -0.8, "market_deposit_base": 10500.0, "market_loan_base": 7500.0,
        "gov_bond_yield": 4.00, "corp_bond_yield": 7.80, "base_npl_rate": 4.2,
        "news_headline": "💥 [금융 위기] 중견기업 연쇄 도산 및 부동산 PF 부실 쇼크!",
        "news_detail": "마이너스 성장에 진입하며 신용위기가 터졌습니다. 은행권 전반에 부실채권(NPL)이 폭증하고 대규모 충당금 전입으로 순이익이 급감합니다.",
        "instructor_tip": "BIS 비율 10.5% 방어가 최대 과제입니다. 충당금 전입과 자본 훼손을 어떻게 극복하는지 관찰하세요.",
        "leading": {
            "cli": "96.8",
            "yield_curve": "-0.15%p",
            "credit_spread": "2.90%p"
        }
    },
    7: {
        "round_name": "Round 7 (8주차)", "phase": "감독당국의 규제 강화",
        "base_rate": 3.75, "gdp_growth": 0.2, "market_deposit_base": 10800.0, "market_loan_base": 7800.0,
        "gov_bond_yield": 3.60, "corp_bond_yield": 6.50, "base_npl_rate": 3.2,
        "news_headline": "📜 [규제 감독] 금융감독원, '은행 자본적정성 관리 강화 및 배당 자제 권고'",
        "news_detail": "감독당국이 부실 은행에 대한 경영개선 권고를 시작했습니다. 배당을 억제하고 이익을 사내 유보하여 자기자본비율을 정상화해야 합니다.",
        "instructor_tip": "위기 극복을 위한 디레버리징(자산 축소) 및 내부유보 중심의 자본 확충 전략을 피드백하세요.",
        "leading": {
            "cli": "99.8",
            "yield_curve": "+0.40%p",
            "credit_spread": "1.60%p"
        }
    },
    8: {
        "round_name": "Round 8 (9주차)", "phase": "금리 인하 사이클 및 경기 회복기",
        "base_rate": 2.75, "gdp_growth": 1.8, "market_deposit_base": 11400.0, "market_loan_base": 8600.0,
        "gov_bond_yield": 2.90, "corp_bond_yield": 4.50, "base_npl_rate": 1.9,
        "news_headline": "🌱 [경기 회복] 한국은행 금리 전격 인하, 시장 정상화 시동",
        "news_detail": "기준금리가 인하되며 채권 가격이 상승(평가이익)하고 대출 수요가 회복됩니다. 건전성을 지켜낸 은행들이 재도약할 기회입니다.",
        "instructor_tip": "금리 하락기에 유가증권(국채/회사채) 포트폴리오가 창출하는 평가이익과 회복세를 확인하세요.",
        "leading": {
            "cli": "101.2",
            "yield_curve": "+0.65%p",
            "credit_spread": "1.25%p"
        }
    },
    9: {
        "round_name": "Round 9 (10주차)", "phase": "최종 결산 라운드",
        "base_rate": 2.50, "gdp_growth": 2.2, "market_deposit_base": 12000.0, "market_loan_base": 9500.0,
        "gov_bond_yield": 2.65, "corp_bond_yield": 3.90, "base_npl_rate": 1.2,
        "news_headline": "🏁 [마지막 분기] 9개 분기 경영 대장정 마무리, 최종 주주가치 결정",
        "news_detail": "모든 시련을 거쳐 최종 결산에 도달했습니다. 최종 배당 정책과 포트폴리오 정리를 통해 최종 기업가치와 누적 ROE를 극대화하세요.",
        "instructor_tip": "최종 순위는 누적 ROE, 최종 주가, BIS 건전성을 종합 평가함을 상기시키세요.",
        "leading": {
            "cli": "101.5",
            "yield_curve": "+0.70%p",
            "credit_spread": "1.20%p"
        }
    }
}

# ==============================================================================
# 3. Google Sheets 클라우드 데이터베이스 연동 관리
# ==============================================================================
LOCAL_CONFIG_FILE = "gsheets_config.json"
LOCAL_DATA_FILE = "bank_game_state.json"

def get_gsheets_url():
    if DEFAULT_GSHEETS_URL and DEFAULT_GSHEETS_URL.startswith("http"):
        return DEFAULT_GSHEETS_URL.strip()
    if os.path.exists(LOCAL_CONFIG_FILE):
        try:
            with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("gsheets_url", "")
        except Exception:
            return ""
    return ""

def set_gsheets_url(url):
    with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"gsheets_url": url.strip()}, f, ensure_ascii=False, indent=2)

def test_gsheets_connection(url):
    if not url or not url.startswith("http"):
        return False, "URL이 올바르지 않습니다. (https://script.google.com/... 형식)"
    try:
        r_get = requests.get(url, timeout=7, allow_redirects=True)
        if r_get.status_code != 200:
            return False, f"구글 시트 응답 실패 (HTTP {r_get.status_code}). '모든 사용자' 배포 권한을 확인하세요."
        return True, "🟢 구글 시트와 정상 연결되었습니다! (동기화 활성화됨)"
    except Exception as e:
        return False, f"연결 오류 발생: {str(e)}"

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
    gs_url = get_gsheets_url()
    if gs_url and gs_url.startswith("http"):
        try:
            resp = requests.get(gs_url, timeout=6, allow_redirects=True)
            if resp.status_code == 200 and resp.text.strip().startswith("{"):
                data = json.loads(resp.text)
                if isinstance(data, dict) and "game_state" in data:
                    with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return _ensure_schema(data)
        except Exception:
            pass
            
    if os.path.exists(LOCAL_DATA_FILE):
        try:
            with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _ensure_schema(data)
        except Exception:
            pass
            
    return _init_default_data()

def _ensure_schema(data):
    if "game_state" not in data: data["game_state"] = {"current_round": 1, "is_finished": False}
    if "users" not in data: data["users"] = {}
    if "teams" not in data: data["teams"] = []
    if "decisions" not in data: data["decisions"] = {}
    if "history" not in data: data["history"] = {}
    
    for t in data["teams"]:
        if "members" not in t:
            t["members"] = []
            if "email" in t and t["email"]:
                t["members"].append({"email": t["email"], "name": t.get("leader_name", "팀장")})
        if "team_pin" not in t:
            t["team_pin"] = ""
            
    return data

def _init_default_data():
    data = {
        "game_state": {"current_round": 1, "is_finished": False},
        "users": {}, "teams": [], "decisions": {}, "history": {}
    }
    _save_data(data)
    return data

def _save_data(data):
    data = _ensure_schema(data)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)
        
    gs_url = get_gsheets_url()
    if gs_url and gs_url.startswith("http"):
        try:
            requests.post(
                gs_url,
                data=json_str.encode("utf-8"),
                headers={"Content-Type": "text/plain;charset=utf-8"},
                timeout=6,
                allow_redirects=True
            )
        except Exception:
            pass

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
        new_deposits = round(deposit_shares[b_id] * (scenario["market_deposit_base"] * scale), 2)
        new_loans = round(loan_shares[b_id] * (scenario["market_loan_base"] * scale), 2)
        required_reserves = round(new_deposits * 0.07, 2)
        
        funding_base = new_deposits + prev["total_equity"]
        operating_need = required_reserves + new_loans
        
        if funding_base >= operating_need:
            total_bonds = round(funding_base - operating_need, 2)
            new_gov_bonds = round(total_bonds * bond_alloc_gov, 2)
            new_corp_bonds = round(total_bonds * (1.0 - bond_alloc_gov), 2)
            new_borrowings = 0.0
        else:
            new_gov_bonds = 50.0
            new_corp_bonds = 30.0
            deficit = (operating_need + new_gov_bonds + new_corp_bonds) - funding_base
            new_borrowings = max(0.0, round(deficit, 2))
            
        uw_npl_mult = 1.6 if underwriting == "공격적" else (0.65 if underwriting == "보수적" else 1.0)
        spread_over_base = max(0.0, r_loan - (scenario["base_rate"] + 2.0))
        adverse_selection = spread_over_base * 0.15
        
        npl_rate = round(scenario["base_npl_rate"] * uw_npl_mult * (1.0 + adverse_selection), 2)
        credit_loss_provision = round(new_loans * (npl_rate / 100.0 / 4.0) * 0.8, 2)
        allowance_losses = round(prev.get("allowance_losses", 10.0) * 0.8 + credit_loss_provision, 2)
        net_loans = round(new_loans - allowance_losses, 2)
        
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
        
        total_assets = round(required_reserves + new_gov_bonds + new_corp_bonds + net_loans, 2)
        total_liabilities = round(new_deposits + new_borrowings, 2)
        
        earning_assets = new_loans + new_gov_bonds + new_corp_bonds
        nim = round((net_interest_income * 4.0 / max(1.0, earning_assets)) * 100.0, 2)
        
        rwa = max(1.0, round(new_loans * 1.0 + new_corp_bonds * 0.5, 2))
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
# 5. 세션 상태 및 자동 로그인 복구
# ==============================================================================
data = _load_data()
game_state = data.get("game_state", {"current_round": 1, "is_finished": False})
curr_round = game_state["current_round"]
is_finished = game_state["is_finished"]

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# 새로고침 시 URL 파라미터를 통한 세션 자동 복구
if st.session_state.auth_user is None:
    param_user, param_admin = get_login_params()
    if param_user and param_user in data.get("users", {}):
        u_info = data["users"][param_user]
        st.session_state.auth_user = {
            "role": "student",
            "email": param_user,
            "name": u_info.get("name", "학생"),
            "bank_id": u_info["bank_id"],
            "bank_name": u_info["bank_name"]
        }
    elif param_admin == "1":
        st.session_state.auth_user = {"role": "admin"}

st.sidebar.markdown("### 🏦 상업은행 경영 시뮬레이션")
st.sidebar.markdown(f"**진행 현황:** {'🏁 결산 완료' if is_finished else f'📍 Round {curr_round} / 9 (총 11주차)'}")

active_gs_url = get_gsheets_url()
if active_gs_url:
    st.sidebar.success("🟢 구글 시트 실시간 연동 중")
else:
    st.sidebar.warning("🟡 구글 시트 URL 미설정 (임시저장)")

if curr_round in SCENARIOS:
    sc = SCENARIOS[curr_round]
    st.sidebar.info(f"**기준금리:** {sc['base_rate']:.2f}%\n\n**성장률:** {sc['gdp_growth']:+.1f}%\n\n**단계:** {sc['phase']}")

if st.session_state.auth_user is not None:
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
        clear_login_params()
        st.session_state.auth_user = None
        st.rerun()

# -------------------------------------------------------------
# [1] 비로그인 상태 (가입 / 로그인 / 관리자접속)
# -------------------------------------------------------------
if st.session_state.auth_user is None:
    st.markdown("<div class='main-title'>🏦 상업은행 경영 시뮬레이션 시스템</div>", unsafe_allow_html=True)
    st.caption("수업에 참여하는 학생은 이메일로 가입/로그인하시고, 교수님은 관리자 탭에서 로그인하세요. (새로고침 로그인 유지 지원)")
    
    login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 학생 로그인", "📝 학생 회원가입 (팀 소속/합류)", "👨‍🏫 교수자(관리자) 접속"])
    
    with login_tab1:
        st.markdown("#### 학생 로그인")
        with st.form("student_login_form"):
            login_email = st.text_input("이메일 주소", placeholder="student@hannam.ac.kr")
            login_pw = st.text_input("비밀번호", type="password")
            btn_login = st.form_submit_button("로그인", use_container_width=True)
            
            if btn_login:
                data = _load_data()
                users = data.get("users", {})
                if login_email in users and users[login_email]["password"] == login_pw:
                    u_info = users[login_email]
                    st.session_state.auth_user = {
                        "role": "student",
                        "email": login_email,
                        "name": u_info.get("name", "학생"),
                        "bank_id": u_info["bank_id"],
                        "bank_name": u_info["bank_name"]
                    }
                    set_login_params("student", login_email)
                    st.success(f"반갑습니다 {u_info.get('name', '')}님! **{u_info['bank_name']}**으로 로그인되었습니다.")
                    st.rerun()
                else:
                    st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
                    
    with login_tab2:
        st.markdown("#### 학생 개별 회원가입 및 팀(은행) 소속 설정")
        st.caption("학생 개개인의 이메일로 가입하되, 팀장이 만든 우리 팀 은행에 합류하여 함께 관리할 수 있습니다!")
        
        teams_list = data.get("teams", [])
        
        with st.form("student_signup_team_form"):
            c_u1, c_u2 = st.columns(2)
            with c_u1:
                reg_email = st.text_input("내 이메일 주소 (아이디로 사용)", placeholder="student1@hannam.ac.kr")
                reg_name = st.text_input("내 이름 (실명 입력)", placeholder="홍길동")
            with c_u2:
                reg_pw = st.text_input("비밀번호 설정", type="password")
                
            st.markdown("---")
            st.markdown("##### 👥 팀(은행) 선택 방식")
            
            join_mode = st.radio(
                "가입 유형을 선택하세요",
                ["✨ 새로운 팀(은행) 새로 만들기 (팀장)", "🤝 이미 만들어진 팀에 합류하기 (팀원)"]
            )
            
            new_team_name = ""
            new_team_pin = ""
            selected_team_id = ""
            input_join_pin = ""
            
            if "새로 만들기" in join_mode:
                st.info("💡 새로운 은행을 설립합니다. 팀원들에게 공유할 '팀 참여 비밀번호(PIN)'를 설정하세요.")
                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    new_team_name = st.text_input("우리 팀 은행 이름 (예: 한남혁신은행, 블루오션뱅크 등)", placeholder="OO은행")
                with c_t2:
                    new_team_pin = st.text_input("팀 참여 비밀번호 (4자리 숫자 등, 팀원 공유용)", placeholder="예: 1234")
            else:
                if not teams_list:
                    st.warning("아직 등록된 팀(은행)이 없습니다. 먼저 팀장이 [새로운 팀 새로 만들기]로 등록해야 합니다.")
                else:
                    st.info("💡 팀장이 이미 생성한 우리 팀 은행을 선택하고, 팀장이 알려준 비밀번호를 입력하세요.")
                    team_choices = {t["bank_id"]: f"{t['bank_name']}" for t in teams_list}
                    c_j1, c_j2 = st.columns(2)
                    with c_j1:
                        selected_team_id = st.selectbox("우리 팀(은행) 선택", list(team_choices.keys()), format_func=lambda x: team_choices[x])
                    with c_j2:
                        input_join_pin = st.text_input("팀 참여 비밀번호 입력", placeholder="팀장에게 받은 비밀번호 입력")
                        
            btn_signup = st.form_submit_button("회원가입 및 팀 소속 완료", use_container_width=True)
            
            if btn_signup:
                data = _load_data()
                if not reg_email or not reg_pw or not reg_name:
                    st.warning("이메일, 이름, 비밀번호를 모두 입력해 주세요.")
                elif reg_email in data.get("users", {}):
                    st.error("이미 가입된 이메일 주소입니다. 로그인을 이용해 주세요.")
                else:
                    if "users" not in data: data["users"] = {}
                    if "teams" not in data: data["teams"] = []
                    if "history" not in data: data["history"] = {}
                    
                    if "새로 만들기" in join_mode:
                        if not new_team_name:
                            st.warning("은행 이름을 입력해 주세요.")
                        else:
                            new_bank_id = f"bank_{len(data['teams']) + 1}_{abs(hash(new_team_name + reg_email)) % 10000}"
                            data["users"][reg_email] = {
                                "password": reg_pw,
                                "name": reg_name,
                                "bank_id": new_bank_id,
                                "bank_name": new_team_name,
                                "is_leader": True
                            }
                            data["teams"].append({
                                "bank_id": new_bank_id,
                                "bank_name": new_team_name,
                                "team_pin": new_team_pin.strip(),
                                "leader_email": reg_email,
                                "members": [{"email": reg_email, "name": f"{reg_name} (팀장)"}]
                            })
                            init_st = get_initial_bank_state(new_bank_id, new_team_name)
                            data["history"][new_bank_id] = [init_st]
                            _save_data(data)
                            st.success(f"🎉 **{new_team_name}**이(가) 성공적으로 창설되었습니다! 팀원들에게 참여 비밀번호({new_team_pin})를 공유하세요. [학생 로그인] 탭에서 로그인해 주세요.")
                    else:
                        target_team = next((t for t in data["teams"] if t["bank_id"] == selected_team_id), None)
                        if not target_team:
                            st.error("선택한 팀을 찾을 수 없습니다.")
                        elif target_team.get("team_pin") and target_team["team_pin"].strip() != input_join_pin.strip():
                            st.error("팀 참여 비밀번호가 일치하지 않습니다. 팀장에게 확인해 주세요.")
                        else:
                            data["users"][reg_email] = {
                                "password": reg_pw,
                                "name": reg_name,
                                "bank_id": target_team["bank_id"],
                                "bank_name": target_team["bank_name"],
                                "is_leader": False
                            }
                            if "members" not in target_team:
                                target_team["members"] = []
                            target_team["members"].append({"email": reg_email, "name": reg_name})
                            _save_data(data)
                            st.success(f"🎉 **{target_team['bank_name']}**에 팀원으로 합류 완료되었습니다! [학생 로그인] 탭에서 로그인해 주세요.")
                    
    with login_tab3:
        st.markdown("#### 교수자 관리자 로그인")
        with st.form("admin_login_form"):
            admin_pw_input = st.text_input("관리자 마스터 비밀번호", type="password", placeholder="비밀번호 입력")
            btn_admin_login = st.form_submit_button("관리자 접속", use_container_width=True)
            if btn_admin_login:
                if admin_pw_input == "admin1234":
                    st.session_state.auth_user = {"role": "admin"}
                    set_login_params("admin")
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
    my_name = user_info.get("name", "학생")
    
    st.markdown(f"<div class='main-title'>🏛️ {my_bank_name} 경영본부</div>", unsafe_allow_html=True)
    
    target_team = next((t for t in data.get("teams", []) if t["bank_id"] == my_bank_id), {})
    members = target_team.get("members", [])
    member_names = ", ".join([m.get("name", m.get("email", "")) for m in members]) if members else my_name
    
    st.markdown(f"""
    <div class='team-badge'>
        👤 로그인: <b>{my_name}</b> ({user_info['email']}) &nbsp;|&nbsp; 👥 <b>우리 팀 소속 팀원:</b> {member_names}
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📢 시장 브리핑 & 경기선행지표", "✍️ 의사결정 제출 (팀 공동)", "📊 우리 은행 재무제표", "🏆 시장 전체 순위"])
    
    with tab1:
        if is_finished:
            st.success("🎉 모든 9개 라운드가 종료되었습니다! 최종 경영 성과를 확인하세요.")
        else:
            sc = SCENARIOS[curr_round]
            st.markdown(f"#### 📅 {sc['round_name']} : {sc['phase']}")
            
            st.markdown(f"""
            <div class='highlight-news'>
                <h3 style='color: #1E3A8A; margin-bottom: 8px;'>{sc['news_headline']}</h3>
                <p style='font-size: 1.05rem; line-height: 1.6; margin-bottom: 0;'>{sc['news_detail']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("한국은행 기준금리", f"{sc['base_rate']:.2f}%")
            c2.metric("실질 GDP 성장률", f"{sc['gdp_growth']:+.1f}%")
            c3.metric("국채 수익률 (무위험)", f"{sc['gov_bond_yield']:.2f}%")
            c4.metric("회사채 수익률 (수익형)", f"{sc['corp_bond_yield']:.2f}%")
            
            st.markdown("---")
            
            # ⭐ [해석 및 설명문이 완전히 제거된 순수 금융 선행지표 수치]
            leading = sc.get("leading", {})
            st.markdown("#### 🔮 주요 금융 선행지표 (Forward-looking Indicators)")
            st.caption("다음 분기 경기 흐름을 예측할 수 있는 핵심 금융 선행지표입니다. 각 지표 수치가 시사하는 바를 팀원들과 직접 분석하여 경영 의사결정에 반영하세요.")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                st.metric("경기선행지수 순환변동치 (CLI)", leading.get("cli", "-"))
            with col_l2:
                st.metric("장단기 국채 금리차 (10년 - 1년)", leading.get("yield_curve", "-"))
            with col_l3:
                st.metric("회사채 신용 스프레드 (AA- 국고채차)", leading.get("credit_spread", "-"))

    with tab2:
        if is_finished:
            st.warning("게임이 종료되어 의사결정이 마감되었습니다.")
        else:
            sc = SCENARIOS[curr_round]
            st.markdown(f"#### 📝 Round {curr_round} 경영 의사결정 입력")
            prev_dec = data.get("decisions", {}).get(f"round_{curr_round}", {}).get(my_bank_id, {})
            
            last_updater = prev_dec.get("updated_by", "")
            if last_updater:
                st.caption(f"ℹ️ 최근 의사결정 저장자: **{last_updater}** (팀원 누구나 내용을 수정하고 덮어쓸 수 있습니다)")
            else:
                st.caption("ℹ️ 선행지표와 경제 브리핑을 분석한 후 팀원들과 상의하여 6개 변수를 결정해 주세요.")
                
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
                    
                if st.form_submit_button("💾 우리 팀 의사결정 저장 및 제출하기", use_container_width=True):
                    clean_uw = "보수적" if "보수" in underwriting else ("공격적" if "공격" in underwriting else "표준")
                    dec_dict = {
                        "deposit_rate": dep_rate, "loan_rate": loan_rate,
                        "underwriting_standard": clean_uw, "marketing_budget": mkt_budget,
                        "bond_allocation_gov": bond_gov, "dividend_payout_ratio": dividend_payout,
                        "updated_by": f"{my_name} ({user_info['email']})"
                    }
                    r_key = f"round_{curr_round}"
                    if r_key not in data["decisions"]: data["decisions"][r_key] = {}
                    data["decisions"][r_key][my_bank_id] = dec_dict
                    _save_data(data)
                    st.success("✅ 우리 팀의 의사결정이 정상 제출되었습니다!")
                    st.rerun()

    with tab3:
        history = data.get("history", {}).get(my_bank_id, [])
        if history:
            latest = history[-1]
            st.markdown(f"#### 📊 {my_bank_name} 경영 성과 리포트 (직전 결산: Round {latest['round']})")
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("주가", f"{latest.get('stock_price', 10000):,.0f} 원")
            k2.metric("BIS 자기자본비율", f"{latest.get('bis_ratio', 12.0):.2f}%")
            k3.metric("순이자마진 (NIM)", f"{latest.get('nim', 2.0):.2f}%")
            k4.metric("당기순이익", f"{fmt_num(latest.get('net_income', 0.0))} 억")
            k5.metric("ROE", f"{latest.get('roe', 0.0):.2f}%")
            k6.metric("부실채권비율 (NPL)", f"{latest.get('npl_ratio', 1.0):.2f}%")
            st.markdown(f"**규제 상태:** {latest.get('regulatory_status', '정상')}")
            st.markdown("---")
            
            c_bs, c_pl = st.columns(2)
            with c_bs:
                bs_items = [
                    "현금 및 지급준비금", "국채 (무위험)", "회사채 (수익형)", "총대출금",
                    " (차감: 대손충당금)", "순대출금", "자산 총계",
                    "총예금", "콜차입금 (단기차입)", "부채 총계",
                    "납입자본금", "이익잉여금", "자본 총계", "부채 및 자본 총계"
                ]
                bs_amounts = [
                    latest.get("cash_reserves", 0), latest.get("gov_bonds", 0), latest.get("corp_bonds", 0), latest.get("gross_loans", 0),
                    f"-{latest.get('allowance_losses', 0)}", latest.get("net_loans", 0), latest.get("total_assets", 0),
                    latest.get("deposits", 0), latest.get("borrowings", 0), latest.get("total_liabilities", 0),
                    latest.get("capital_stock", 0), latest.get("retained_earnings", 0), latest.get("total_equity", 0), latest.get("total_assets", 0)
                ]
                st.markdown(render_financial_html_table("🏛️ 재무상태표 (Balance Sheet)", bs_items, bs_amounts), unsafe_allow_html=True)
                
            with c_pl:
                pl_items = [
                    "이자수익 (대출 + 채권)", "이자비용 (예금 + 차입)", "순이자이익 (NII)",
                    "유가증권 평가손익", "판매비와관리비 (판관비)", "대손충당금 전입액",
                    "세전순이익 (법인세차감전)", "법인세비용 (20%)", "당기순이익 (분기)",
                    "배당금 지급액", "사내유보 이익잉여금"
                ]
                retained_added = round(latest.get("net_income", 0) - latest.get("dividend_paid", 0), 2)
                pl_amounts = [
                    latest.get("interest_income", 0), latest.get("interest_expense", 0), latest.get("net_interest_income", 0),
                    latest.get("bond_valuation_gain", 0), latest.get("sga_expense", 0), latest.get("credit_loss_provision", 0),
                    latest.get("pretax_income", 0), latest.get("tax_expense", 0), latest.get("net_income", 0),
                    latest.get("dividend_paid", 0), retained_added
                ]
                st.markdown(render_financial_html_table("📈 손익계산서 (Income Statement)", pl_items, pl_amounts), unsafe_allow_html=True)
                
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
                    "주가 (원)": f"{last_s.get('stock_price', 10000):,.0f}",
                    "누적 ROE (%)": f"{last_s.get('cumulative_roe', 0.0):.2f}",
                    "BIS 비율 (%)": f"{last_s.get('bis_ratio', 12.0):.2f}",
                    "총자산 (억원)": f"{last_s.get('total_assets', 0):,.2f}",
                    "예금점유율 (%)": f"{last_s.get('deposit_share', 0):.1f}",
                    "대출점유율 (%)": f"{last_s.get('loan_share', 0):.1f}",
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
    
    adm_tab1, adm_tab2, adm_tab3, adm_tab4 = st.tabs([
        "🕹️ 라운드 진행 및 결산",
        "🌐 현재 경제상황 & 팀별 재무지표 비교",
        "📑 팀별 재무제표 (BS/PL) 상세 열람",
        "⚙️ 구글시트 연동 & 은행 관리"
    ])
    
    # Tab 1: 라운드 진행 및 결산
    with adm_tab1:
        st.markdown(f"### 📍 현재 진행 단계: **Round {curr_round} / 9**")
        if is_finished:
            st.success("🏁 9라운드 시뮬레이션이 모두 마감되었습니다.")
        else:
            sc = SCENARIOS.get(curr_round, {})
            st.info(f"**이번 라운드 시나리오:** {sc.get('news_headline', '')}\n\n💡 **교수자 가이드 팁:** {sc.get('instructor_tip', '')}")
            
            decisions_curr = data.get("decisions", {}).get(f"round_{curr_round}", {})
            teams_list = data.get("teams", [])
            
            st.markdown(f"#### 📋 등록된 학생 은행 ({len(teams_list)}개) 및 소속 팀원 제출 현황")
            if not teams_list:
                st.warning("아직 학생들이 가입하여 설립한 은행이 없습니다.")
            else:
                status_data = []
                for t in teams_list:
                    b_id = t["bank_id"]
                    submitted = b_id in decisions_curr
                    dec = decisions_curr.get(b_id, {})
                    members_str = ", ".join([m.get("name", m.get("email", "")) for m in t.get("members", [])])
                    if not members_str:
                        members_str = t.get("email", "-")
                        
                    status_data.append({
                        "은행명": t["bank_name"],
                        "소속 팀원 목록": members_str,
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
                                "bond_allocation_gov": 70.0, "dividend_payout_ratio": 20.0,
                                "updated_by": "시스템 기본값"
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

    # Tab 2: 현재 경제상황 & 팀별 재무지표 비교
    with adm_tab2:
        sc = SCENARIOS.get(curr_round, {})
        st.markdown(f"### 🌐 Round {curr_round} 거시경제 상황 요약")
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("한국은행 기준금리", f"{sc.get('base_rate', 0):.2f}%")
        c_m2.metric("실질 GDP 성장률", f"{sc.get('gdp_growth', 0):+.1f}%")
        c_m3.metric("국채 수익률", f"{sc.get('gov_bond_yield', 0):.2f}%")
        c_m4.metric("회사채 수익률", f"{sc.get('corp_bond_yield', 0):.2f}%")
        
        st.markdown(f"""
        <div class='highlight-news'>
            <b>{sc.get('news_headline', '')}</b><br>
            {sc.get('news_detail', '')}
        </div>
        """, unsafe_allow_html=True)
        
        lead = sc.get("leading", {})
        c_ld1, c_ld2, c_ld3 = st.columns(3)
        c_ld1.metric("경기선행지수 (CLI)", lead.get("cli", "-"))
        c_ld2.metric("장단기 국채 금리차", lead.get("yield_curve", "-"))
        c_ld3.metric("회사채 신용스프레드", lead.get("credit_spread", "-"))
        
        st.markdown("---")
        st.markdown("### 📊 전체 팀 재무지표 종합 비교")
        teams_list = data.get("teams", [])
        
        kpi_list = []
        for t in teams_list:
            t_hist = data.get("history", {}).get(t["bank_id"], [])
            if t_hist:
                last_s = t_hist[-1]
                m_names = ", ".join([m.get("name", "") for m in t.get("members", [])])
                kpi_list.append({
                    "은행명": last_s["bank_name"],
                    "소속 팀원": m_names if m_names else t.get("email", "-"),
                    "주가 (원)": f"{last_s.get('stock_price', 10000):,.0f}",
                    "당기순이익 (억)": f"{fmt_num(last_s.get('net_income', 0))}",
                    "ROE (%)": f"{last_s.get('roe', 0.0):.2f}",
                    "NIM (%)": f"{last_s.get('nim', 2.0):.2f}",
                    "BIS 비율 (%)": f"{last_s.get('bis_ratio', 12.0):.2f}",
                    "NPL 부실률 (%)": f"{last_s.get('npl_ratio', 1.0):.2f}",
                    "총자산 (억)": f"{last_s.get('total_assets', 0):,.2f}",
                    "총예금 (억)": f"{last_s.get('deposits', 0):,.2f}",
                    "총대출 (억)": f"{last_s.get('gross_loans', 0):,.2f}",
                    "규제 상태": last_s.get("regulatory_status", "정상")
                })
        if kpi_list:
            df_kpi = pd.DataFrame(kpi_list).sort_values(by="주가 (원)", ascending=False).reset_index(drop=True)
            df_kpi.index = df_kpi.index + 1
            st.dataframe(df_kpi, use_container_width=True)
            
            all_histories = [record for t in teams_list for record in data.get("history", {}).get(t["bank_id"], [])]
            if len(all_histories) > len(teams_list):
                df_all = pd.DataFrame(all_histories)
                df_pivot_stock = df_all.pivot(index="round", columns="bank_name", values="stock_price")
                df_pivot_bis = df_all.pivot(index="round", columns="bank_name", values="bis_ratio")
                
                c_ch1, c_ch2 = st.columns(2)
                with c_ch1:
                    st.markdown("##### 📈 팀별 주가 추이 (원)")
                    st.line_chart(df_pivot_stock)
                with c_ch2:
                    st.markdown("##### 🛡️ 팀별 BIS 자기자본비율 추이 (%)")
                    st.line_chart(df_pivot_bis)
                    
            csv_data = pd.DataFrame(all_histories).to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 결산 데이터 다운로드 (CSV)", csv_data, "bank_game_results.csv", "text/csv", use_container_width=True)
        else:
            st.info("등록된 팀의 결산 데이터가 없습니다.")

    # Tab 3: 팀별 재무제표 (BS/PL) 상세 열람
    with adm_tab3:
        st.markdown("### 📑 팀별 상세 재무제표 (BS & PL) 열람")
        st.caption("특정 팀의 재무상태표와 손익계산서를 학생 화면과 동일한 회계 서식으로 정밀 점검할 수 있습니다.")
        
        teams_list = data.get("teams", [])
        if not teams_list:
            st.warning("등록된 팀이 없습니다.")
        else:
            team_map = {t["bank_id"]: t["bank_name"] for t in teams_list}
            sel_b_id = st.selectbox("열람할 은행 선택", list(team_map.keys()), format_func=lambda x: team_map[x])
            
            t_obj = next((t for t in teams_list if t["bank_id"] == sel_b_id), {})
            t_members = ", ".join([m.get("name", m.get("email", "")) for m in t_obj.get("members", [])])
            st.markdown(f"**소속 팀원:** `{t_members}`")
            
            t_history = data.get("history", {}).get(sel_b_id, [])
            if not t_history:
                st.info("해당 팀의 재무 기록이 없습니다.")
            else:
                round_options = [s["round"] for s in t_history]
                sel_rnd = st.select_slider("조회할 라운드 선택", options=round_options, value=round_options[-1])
                
                target_state = next((s for s in t_history if s["round"] == sel_rnd), t_history[-1])
                
                st.markdown(f"#### 📊 {team_map[sel_b_id]} - Round {sel_rnd} 재무 성과 요약")
                ak1, ak2, ak3, ak4, ak5, ak6 = st.columns(6)
                ak1.metric("주가", f"{target_state.get('stock_price', 10000):,.0f} 원")
                ak2.metric("BIS 자기자본비율", f"{target_state.get('bis_ratio', 12.0):.2f}%")
                ak3.metric("NIM", f"{target_state.get('nim', 2.0):.2f}%")
                ak4.metric("당기순이익", f"{fmt_num(target_state.get('net_income', 0.0))} 억")
                ak5.metric("ROE", f"{target_state.get('roe', 0.0):.2f}%")
                ak6.metric("NPL 부실률", f"{target_state.get('npl_ratio', 1.0):.2f}%")
                st.markdown(f"**규제 상태:** {target_state.get('regulatory_status', '정상')}")
                st.markdown("---")
                
                col_bs, col_pl = st.columns(2)
                with col_bs:
                    bs_items = [
                        "현금 및 지급준비금", "국채 (무위험)", "회사채 (수익형)", "총대출금",
                        " (차감: 대손충당금)", "순대출금", "자산 총계",
                        "총예금", "콜차입금 (단기차입)", "부채 총계",
                        "납입자본금", "이익잉여금", "자본 총계", "부채 및 자본 총계"
                    ]
                    bs_amounts = [
                        target_state.get("cash_reserves", 0), target_state.get("gov_bonds", 0), target_state.get("corp_bonds", 0), target_state.get("gross_loans", 0),
                        f"-{target_state.get('allowance_losses', 0)}", target_state.get("net_loans", 0), target_state.get("total_assets", 0),
                        target_state.get("deposits", 0), target_state.get("borrowings", 0), target_state.get("total_liabilities", 0),
                        target_state.get("capital_stock", 0), target_state.get("retained_earnings", 0), target_state.get("total_equity", 0), target_state.get("total_assets", 0)
                    ]
                    st.markdown(render_financial_html_table(f"🏛️ {team_map[sel_b_id]} 재무상태표 (Round {sel_rnd})", bs_items, bs_amounts), unsafe_allow_html=True)
                    
                with col_pl:
                    pl_items = [
                        "이자수익 (대출 + 채권)", "이자비용 (예금 + 차입)", "순이자이익 (NII)",
                        "유가증권 평가손익", "판매비와관리비 (판관비)", "대손충당금 전입액",
                        "세전순이익 (법인세차감전)", "법인세비용 (20%)", "당기순이익 (분기)",
                        "배당금 지급액", "사내유보 이익잉여금"
                    ]
                    retained_added = round(target_state.get("net_income", 0) - target_state.get("dividend_paid", 0), 2)
                    pl_amounts = [
                        target_state.get("interest_income", 0), target_state.get("interest_expense", 0), target_state.get("net_interest_income", 0),
                        target_state.get("bond_valuation_gain", 0), target_state.get("sga_expense", 0), target_state.get("credit_loss_provision", 0),
                        target_state.get("pretax_income", 0), target_state.get("tax_expense", 0), target_state.get("net_income", 0),
                        target_state.get("dividend_paid", 0), retained_added
                    ]
                    st.markdown(render_financial_html_table(f"📈 {team_map[sel_b_id]} 손익계산서 (Round {sel_rnd})", pl_items, pl_amounts), unsafe_allow_html=True)

    # Tab 4: 구글시트 연동 & 은행 관리
    with adm_tab4:
        st.markdown("### ⚙️ 구글 시트 연동 설정 & 참여 은행 관리")
        
        st.markdown("#### ☁️ Google Sheets 클라우드 DB 연동")
        current_gs_url = get_gsheets_url()
        
        c_url1, c_url2 = st.columns([3, 1])
        with c_url1:
            input_url = st.text_input("구글 Apps Script 웹 앱 URL", value=current_gs_url, placeholder="https://script.google.com/macros/s/.../exec")
        with c_url2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔍 연결 상태 테스트"):
                is_ok, msg = test_gsheets_connection(input_url)
                if is_ok:
                    set_gsheets_url(input_url)
                    st.success(msg)
                else:
                    st.error(msg)
                    
        if st.button("💾 URL 저장 및 동기화 시작", type="primary"):
            if input_url:
                set_gsheets_url(input_url)
                _save_data(data)
                st.success("✅ 구글 시트 URL이 성공적으로 저장되고 현재 데이터가 구글 시트에 즉시 업로드되었습니다!")
                st.rerun()
            else:
                st.warning("URL을 입력해 주세요.")
                
        st.markdown("---")
        
        teams_list = data.get("teams", [])
        st.markdown("#### 🗑️ 특정 팀(은행) 삭제")
        st.caption("테스트로 생성된 팀이나 수강 취소 등으로 삭제가 필요한 팀을 선택하여 제거할 수 있습니다.")
        if teams_list:
            del_options = {t["bank_id"]: f"{t['bank_name']} (팀원: {len(t.get('members', []))}명)" for t in teams_list}
            target_del_id = st.selectbox("삭제할 팀(은행) 선택", list(del_options.keys()), format_func=lambda x: del_options[x])
            
            if st.button("🚨 [선택한 팀 완전 삭제]", type="secondary"):
                del_bank_name = del_options[target_del_id]
                data["teams"] = [t for t in data["teams"] if t["bank_id"] != target_del_id]
                emails_to_del = [em for em, u in data.get("users", {}).items() if u.get("bank_id") == target_del_id]
                for em in emails_to_del:
                    del data["users"][em]
                if target_del_id in data.get("history", {}):
                    del data["history"][target_del_id]
                for r_k in data.get("decisions", {}):
                    if target_del_id in data["decisions"][r_k]:
                        del data["decisions"][r_k][target_del_id]
                        
                _save_data(data)
                st.success(f"✅ **{del_bank_name}**이(가) 정상적으로 삭제되었습니다.")
                st.rerun()
        else:
            st.info("현재 등록된 팀이 없습니다.")
            
        st.markdown("---")
        
        st.markdown("#### ⚠️ 전체 게임 및 등록 계정 초기화")
        st.caption("새 학기 시작 시 모든 등록 계정과 게임 기록을 완전히 비우고 Round 1로 리셋합니다.")
        if st.button("⚠️ [주의] 게임 전체 데이터 초기화"):
            data = {
                "game_state": {"current_round": 1, "is_finished": False},
                "users": {}, "teams": [], "decisions": {}, "history": {}
            }
            _save_data(data)
            st.warning("전체 데이터가 초기화되었습니다. 학생들이 새롭게 가입할 수 있습니다.")
            st.rerun()
