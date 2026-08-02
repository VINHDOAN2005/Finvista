
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from src.core.database import SessionLocal, MarketOpportunity
from src.modules.trading_engine.ai_committee_service import AICommitteeService
from src.core.utils import logger
from sqlalchemy import func
from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector

class GlobalAlphaEngine:
    """
    Unified Top-Down Probabilistic Engine for Market-Wide Alpha Discovery.
    Supports both AI-Deep Scanning and Fast Quantitative Fallback.
    """

    def __init__(self, use_ai: bool = True):
        self.ai_committee = AICommitteeService()
        self.use_ai = use_ai

    def _calculate_dynamic_market_regime(self) -> Dict[str, Any]:
        """
        Dynamically calculates the market regime based on recent VNINDEX history using
        the advanced 4-state Gaussian Hidden Markov Model (HMM).
        """
        try:
            from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            regime = calculate_vnindex_regime(days=1250)
            return regime
        except Exception as e:
            logger.error(f"❌ Error importing or calculating HMM dynamic market regime: {e}. Using fallback.")
            return {
                "regime": "BULLISH_VOL_EXPANSION",
                "confidence": 0.72,
                "bias": "LONG_CW",
                "state": 1,
                "description": "Fallback regime (HMM execution failed)."
            }

    async def run_top_down_scan(self):
        mode_str = "AI-DEEP" if self.use_ai else "QUANT-FAST"
        logger.info(f"🚀 STARTING GLOBAL ALPHA SCAN ({mode_str} MODE)...")
        
        # 🟢 STEP 1: GLOBAL CONTEXT (Calculated dynamically)
        market_regime = self._calculate_dynamic_market_regime()
        
        db = SessionLocal()
        try:
            # 🟢 STEP 2: LOAD OPPORTUNITIES
            opportunities = db.query(MarketOpportunity).all()
            df = pd.DataFrame([vars(o) for o in opportunities])
            
            if df.empty:
                logger.error("❌ No opportunities found in DB.")
                return

            if self.use_ai:
                results = await self._run_ai_scan(df, market_regime)
            else:
                results = await self._run_quant_scan(df, market_regime)
            
            # 🟢 STEP 3: GENERATE FINAL MAP
            self._print_global_alpha_map(market_regime, results)
            
        finally:
            db.close()

    async def _run_ai_scan(self, df: pd.DataFrame, regime: Dict) -> List[Dict]:
        """Deep AI-driven analysis by sector."""
        def get_sector(ticker):
            banks = ['ACB', 'MBB', 'TCB', 'STB', 'HDB', 'VPB', 'VIB', 'LPB', 'SHB', 'SSB', 'TPB', 'CTG', 'VCB']
            steel = ['HPG', 'HSG', 'NKG']
            retail = ['MWG', 'FRT', 'PNJ', 'DGW']
            realestate = ['VHM', 'VIC', 'VRE', 'NVL', 'DXG', 'DIG', 'PDR']
            tech = ['FPT', 'CMG', 'CTR']
            if ticker in banks: return "Banking"
            if ticker in steel: return "Steel"
            if ticker in retail: return "Retail"
            if ticker in realestate: return "Real Estate"
            if ticker in tech: return "Technology"
            return "Others"

        df['sector'] = df['underlying'].apply(get_sector)
        sector_groups = df.groupby('sector')
        
        results = []
        for sector, group in sector_groups:
            logger.info(f"🧠 Sector: {sector} ({len(group)} warrants)...")
            warrants_list = group.to_dict('records')
            
            # Process in chunks to avoid API limits
            chunk_size = 10
            for i in range(0, len(warrants_list), chunk_size):
                chunk = warrants_list[i:i + chunk_size]
                try:
                    batch_audits = await self.ai_committee.analyze_sector_master_deep(sector, chunk, regime)
                    if batch_audits:
                        for symbol, audit in batch_audits.items():
                            if audit.get("status") == "completed":
                                self._update_db_record(symbol, audit)
                                results.append(audit)
                    await asyncio.sleep(15) # Cooldown
                except Exception as e:
                    logger.error(f"❌ AI Audit failed for chunk in {sector}: {e}")
            
            await asyncio.sleep(30) # Sector cooldown
        return results

    async def _run_quant_scan(self, df: pd.DataFrame, regime: Dict) -> List[Dict]:
        """Pure mathematical analysis for fast results."""
        results = []
        is_crisis = regime.get('state') == 3
        if is_crisis:
            logger.warning("🦅 VULTURE MODE ACTIVATED: Searching for high-credit gems in market panic.")

        for _, row in df.iterrows():
            g_score = row.get('score', 50)
            upside = row.get('upside_pct', 0)
            credit_prob = row.get('underlying_distress_prob', 0.1)
            altman_z = row.get('underlying_altman_z', 3.0)
            days_left = row.get('days_to_maturity', 100)
            
            # 🛡️ SURVIVAL FILTER: Never buy CWs close to expiry (Theta Bomb protection)
            if days_left < 25:
                decision = "SKIP (Too close to expiry)"
                rationale = f"Maturity Alert: Only {days_left} days left. High risk of total loss via Theta decay."
                ev_score = 0
            else:
                bull_prob = min(85, max(10, g_score * 0.8 + (upside / 2)))
                if credit_prob > 0.3: bull_prob *= 0.5
                
                bear_prob = max(5, 100 - bull_prob - 20)
                base_prob = 100 - bull_prob - bear_prob
                ev_score = min(100, max(0, (bull_prob * 0.9) + (base_prob * 0.1) - (bear_prob * 0.5)))
                
                decision = "SKIP"
                rationale = f"Quant-Score: {g_score:.1f}, Upside: {upside:.1f}%, Credit: {'Safe' if credit_prob < 0.2 else 'Watch'}"
                
                # 🦅 VULTURE LOGIC: In crisis, if company is rock-solid (Safe Z-Score, Low Prob), we buy the dip.
                if is_crisis and altman_z > 2.6 and credit_prob < 0.12:
                    # Preference for longer-dated warrants in Vulture mode
                    if days_left > 60:
                        ev_score += 30 # Maximum conviction for long-dated survivors
                        decision = "VULTURE STRONG BUY"
                        rationale = f"🦅 VULTURE OP: High-Quality Survivor (Z={altman_z:.1f}) with {days_left}d maturity."
                    else:
                        ev_score += 15 # Lower conviction for shorter-dated survivors
                        decision = "VULTURE BUY"
                        rationale = f"🦅 VULTURE OP: Solid credit (Z={altman_z:.1f}), but shorter maturity ({days_left}d)."
                else:
                    if ev_score > 70: decision = "STRONG BUY"
                    elif ev_score > 55: decision = "BUY"
                    elif ev_score > 40: decision = "HOLD"
                    
                    # In crisis, standard logic is more punishing
                    if is_crisis and decision in ["BUY", "STRONG BUY"]:
                        decision = "HOLD (Wait for Bottom)"
                        ev_score -= 10
            
            audit_data = {
                "symbol": row['symbol'],
                "underlying": row['underlying'],
                "scenarios": {
                    "bull_case": {"prob": float(bull_prob) if 'bull_prob' in locals() else 0},
                    "base_case": {"prob": float(base_prob) if 'base_prob' in locals() else 0},
                    "bear_case": {"prob": float(bear_prob) if 'bear_prob' in locals() else 0}
                },
                "decision": {
                    "decision": decision, 
                    "expected_value_score": float(ev_score),
                    "rationale_summary": rationale
                }
            }
            self._update_db_record(row['symbol'], audit_data)
            results.append(audit_data)
        return results

    def _update_db_record(self, symbol: str, audit: Dict):
        """Update MarketOpportunity in database with analysis results."""
        db = SessionLocal()
        try:
            opp = db.query(MarketOpportunity).filter(MarketOpportunity.symbol == symbol).first()
            if opp:
                scen = audit.get('scenarios', {})
                dec = audit.get('decision', {})
                opp.bull_prob = scen.get('bull_case', {}).get('prob', 0)
                opp.base_prob = scen.get('base_case', {}).get('prob', 0)
                opp.bear_prob = scen.get('bear_case', {}).get('prob', 0)
                opp.ev_score = dec.get('expected_value_score', 0)
                opp.scenario_rationale = dec.get('rationale_summary', '')
                db.commit()
        finally:
            db.close()

    def _print_global_alpha_map(self, regime: Dict, results: List[Dict]):
        print("\n" + "═"*100)
        mode_label = "AI-DEEP" if self.use_ai else "QUANT-FALLBACK"
        print(f"🌍 FINVISTA GLOBAL ALPHA MAP ({mode_label})")
        print("═"*100)
        regime_val = regime.get('regime', 'N/A')
        confidence = regime.get('confidence', 0)
        if isinstance(confidence, str):
            conf_str = confidence
        else:
            conf_str = f"{confidence:.0%}"
        print(f"📈 MARKET REGIME: {regime_val} (Confidence: {conf_str})")
        print(f"🧭 BIAS: {regime.get('bias', 'N/A')}")
        print("-" * 100)
        print(f"{'CW SYMBOL':<12} | {'UNDERLYING':<10} | {'BULL %':<8} | {'EV SCORE':<10} | {'SIGNAL'}")
        print("-" * 100)
        
        sorted_results = sorted(results, key=lambda x: x.get('decision', {}).get('expected_value_score', 0), reverse=True)
        
        for r in sorted_results[:30]:
            symbol = r.get('symbol', 'N/A')
            underlying = r.get('underlying', 'N/A')
            dec = r.get('decision', {})
            bull_prob = r.get('scenarios', {}).get('bull_case', {}).get('prob', 0)
            ev_score = dec.get('expected_value_score', 0)
            
            print(f"{symbol:<12} | {underlying:<10} | {bull_prob:>7.1f}% | {ev_score:>10.1f} | {dec.get('decision', 'HOLD')}")
            
        print("═"*100)

if __name__ == "__main__":
    import sys
    use_ai = "--quant" not in sys.argv
    engine = GlobalAlphaEngine(use_ai=use_ai)
    asyncio.run(engine.run_top_down_scan())
