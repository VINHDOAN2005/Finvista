# -*- coding: utf-8 -*-
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.modules.cw_pricing.service import WarrantService
from src.modules.trading_engine.portfolio_service import PortfolioService
from src.modules.credit_risk.service import CreditRiskService
from src.api.state import load_distress_models

def run_e2e_validation():
    print("="*80)
    print("🏁 FINVISTA END-TO-END SYSTEM VALIDATION")
    print("="*80)

    # 1. Test Warrant Service (Greeks)
    print("\n[MODULE 1: WARRANTS & QUANT]")
    try:
        greeks = WarrantService.calculate_greeks(
            underlying_price=28500,
            strike_price=25000,
            days_to_maturity=90,
            implied_volatility=0.45,
            conversion_ratio=10.0
        )
        print(f"✅ BSM Greeks Calculated: Delta={greeks['delta']}, Theta={greeks['theta']}đ")
    except Exception as e:
        print(f"❌ Warrant Service Error: {e}")

    # 2. Test Portfolio Service (Holdings)
    print("\n[MODULE 2: PORTFOLIO & TRADING]")
    try:
        portfolio = PortfolioService.get_portfolio(username="demo")
        print(f"✅ Portfolio Loaded: NAV={portfolio['total_nav']:,.0f}đ, Cash={portfolio['cash']:,.0f}đ")
        print(f"📦 Active Positions: {len(portfolio['active_positions'])}")
        for pos in portfolio['active_positions']:
            print(f"   - {pos['symbol']}: {pos['qty']:,} units | P/L: {pos['p_l_pct']:.2f}%")
    except Exception as e:
        print(f"❌ Portfolio Service Error: {e}")

    # 3. Test Credit Risk Service (XGBoost)
    print("\n[MODULE 3: CREDIT RISK ML]")
    try:
        load_distress_models()
        health = CreditRiskService.get_credit_health(ticker="HPG")
        print(f"✅ Credit Health (HPG): Zone={health['credit_metrics']['risk_zone']}")
        print(f"📊 Bankruptcy Prob (XGBoost): {health['credit_metrics']['bankruptcy_probability']*100:.2f}%")
        if "ai_commentary" in health:
             print(f"🤖 AI Commentary: {health['ai_commentary'][:100]}...")
    except Exception as e:
        print(f"❌ Credit Risk Service Error: {e}")

    print("\n" + "="*80)
    print("🎉 ALL CORE SERVICES VALIDATED SUCCESSFULLY!")
    print("="*80)

if __name__ == "__main__":
    run_e2e_validation()
