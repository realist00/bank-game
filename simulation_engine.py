# simulation_engine.py - 상업은행 시뮬레이션 계산 엔진

import math
from scenarios import SCENARIOS

def get_initial_bank_state(bank_id, bank_name):
    """0라운드(기초 상태) 은행 재무 데이터 생성 (단위: 억원)"""
    return {
        "round": 0,
        "bank_id": bank_id,
        "bank_name": bank_name,
        
        # 재무상태표 (BS)
        "cash_reserves": 175.0,     # 현금 및 지급준비금 (예금의 7%)
        "gov_bonds": 250.0,         # 국채
        "corp_bonds": 125.0,        # 회사채
        "gross_loans": 2000.0,      # 총대출금
        "allowance_losses": 10.0,   # 대손충당금
        "net_loans": 1990.0,        # 순대출금
        "total_assets": 2540.0,     # 총자산
        
        "deposits": 2500.0,         # 총예금
        "borrowings": 0.0,          # 콜차입 / 단기차입
        "total_liabilities": 2500.0,# 총부채
        
        "capital_stock": 200.0,     # 납입자본금
        "retained_earnings": 50.0,  # 이익잉여금
        "total_equity": 250.0,      # 총자본
        
        # 손익계산서 (PL)
        "interest_income": 27.5,
        "interest_expense": 15.6,
        "net_interest_income": 11.9,
        "bond_valuation_gain": 0.0,
        "sga_expense": 4.5,
        "credit_loss_provision": 2.0,
        "pretax_income": 5.4,
        "tax_expense": 1.08,
        "net_income": 4.32,
        "dividend_paid": 0.86,
        
        # 경영 지표
        "nim": 2.00,                # 순이자마진 (%)
        "bis_ratio": 12.12,         # BIS 자기자본비율 (%)
        "npl_ratio": 1.00,          # 고정이하여신비율 (%)
        "roe": 7.00,                # 자기자본이익률 (%)
        "roa": 0.70,                # 총자산이익률 (%)
        "stock_price": 10000.0,     # 주가 (원)
        "cumulative_roe": 0.0,      # 누적 ROE (%)
        "deposit_share": 25.0,
        "loan_share": 25.0,
        "regulatory_status": "✅ 정상 (규제 통과)"
    }

def process_simulation_round(current_round, decisions_by_bank, previous_states_by_bank):
    """분기별 시뮬레이션 연산 (시장점유율, ALM, 결산)"""
    scenario = SCENARIOS[current_round]
    prev_scenario = SCENARIOS.get(current_round - 1, {
        "gov_bond_yield": scenario["gov_bond_yield"],
        "corp_bond_yield": scenario["corp_bond_yield"]
    })
    
    bank_ids = list(decisions_by_bank.keys())
    if not bank_ids:
        return {}
    
    # 1. 로짓 모형 기반 시장점유율 계산
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
        deposit_scores[b_id] = dep_score
        
        loan_score = math.exp(-0.8 * (r_loan - (scenario["base_rate"] + 2.2)) + 0.30 * math.log(max(0.5, mkt_budget)) + uw_loan_bonus)
        loan_scores[b_id] = loan_score
        
    sum_dep_scores = sum(deposit_scores.values())
    sum_loan_scores = sum(loan_scores.values())
    
    deposit_shares = {b_id: deposit_scores[b_id] / sum_dep_scores for b_id in bank_ids}
    loan_shares = {b_id: loan_scores[b_id] / sum_loan_scores for b_id in bank_ids}
    
    # 2. 은행별 결산 및 지표 산출
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
        
        new_deposits = round(deposit_shares[b_id] * scenario["market_deposit_base"], 1)
        new_loans = round(loan_shares[b_id] * scenario["market_loan_base"], 1)
        required_reserves = round(new_deposits * 0.07, 1) # 지준율 7%
        
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
        
        if bis_ratio < 8.0:
            regulatory_status = "🚨 경영개선명령 (영업정지 위기)"
        elif bis_ratio < 10.5:
            regulatory_status = "⚠️ 경영개선권고 (자본확충 필요)"
        else:
            regulatory_status = "✅ 정상 (규제 통과)"
            
        bps = (new_total_equity / 200.0) * 10000.0
        pbr_mult = max(0.4, min(2.0, 1.0 + (roe - 7.0) * 0.04 + (bis_ratio - 10.5) * 0.03))
        stock_price = max(1000.0, round(bps * pbr_mult, 0))
        
        new_states[b_id] = {
            "round": current_round,
            "bank_id": b_id,
            "bank_name": prev["bank_name"],
            "cash_reserves": required_reserves,
            "gov_bonds": new_gov_bonds,
            "corp_bonds": new_corp_bonds,
            "gross_loans": new_loans,
            "allowance_losses": allowance_losses,
            "net_loans": net_loans,
            "total_assets": total_assets,
            "deposits": new_deposits,
            "borrowings": new_borrowings,
            "total_liabilities": total_liabilities,
            "capital_stock": prev["capital_stock"],
            "retained_earnings": new_retained_earnings,
            "total_equity": new_total_equity,
            "interest_income": total_interest_income,
            "interest_expense": total_interest_expense,
            "net_interest_income": net_interest_income,
            "bond_valuation_gain": bond_gain_loss,
            "sga_expense": sga_expense,
            "credit_loss_provision": credit_loss_provision,
            "pretax_income": pretax_income,
            "tax_expense": tax_expense,
            "net_income": net_income,
            "dividend_paid": dividend_paid,
            "nim": nim,
            "bis_ratio": bis_ratio,
            "npl_ratio": npl_rate,
            "roe": roe,
            "roa": roa,
            "cumulative_roe": cumulative_roe,
            "stock_price": stock_price,
            "deposit_share": round(deposit_shares[b_id] * 100.0, 1),
            "loan_share": round(loan_shares[b_id] * 100.0, 1),
            "regulatory_status": regulatory_status
        }
    return new_states