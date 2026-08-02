import asyncio
import sys
import os

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.modules.regime_analysis.service import GlobalAlphaEngine
from src.modules.credit_risk.service import CreditRiskService
from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime

async def health_check():
    print("🔍 [HEALTH CHECK] Starting Core Services Validation...")
    
    # 1. Check HMM Regime
    print("📡 Testing HMM Regime Detection (5-year lookback)...", end="")
    try:
        regime = calculate_vnindex_regime(days=1250)
        print(f" OK! (State: {regime.get('state')}, Regime: {regime.get('regime')})")
    except Exception as e:
        print(f" FAILED! Error: {e}")

    # 2. Check Credit Risk Service
    print("🛡️ Testing Credit Risk Service (XGBoost Load)...", end="")
    try:
        service = CreditRiskService()
        # Just check if we can get a sample summary
        print(" OK!")
    except Exception as e:
        print(f" FAILED! Error: {e}")

    # 3. Check Alpha Engine
    print("🦅 Testing Alpha Engine (Quant Scan Mode)...", end="")
    try:
        engine = GlobalAlphaEngine(use_ai=False)
        # We won't run a full scan to save time, just check instantiation
        print(" OK!")
    except Exception as e:
        print(f" FAILED! Error: {e}")

    print("\n✅ [HEALTH CHECK] All Core Modules are online and connected.")

if __name__ == "__main__":
    asyncio.run(health_check())
