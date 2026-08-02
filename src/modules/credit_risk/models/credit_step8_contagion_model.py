# -*- coding: utf-8 -*-
"""
🏆 FINVISTA CREDIT RISK PIPELINE — STEP 8: SYSTEMIC CONTAGION MODEL (DebtRank)
=============================================================================
Mô phỏng lan truyền rủi ro hệ thống theo thuật toán DebtRank cải tiến
trên đồ thị mạng lưới thị trường chứng khoán Việt Nam.
Xuất báo cáo systemic_health_report.csv được dùng làm Hard-Gate cho CW Pricing.

CLI: python run.py credit --contagion

Author: samvo
"""

import pandas as pd
import numpy as np
import networkx as nx
from src.core.utils import logger
from src.modules.credit_risk.systemic.network_builder import build_market_network

def run_debtrank_contagion(G, damping_factor=0.25, max_iter=20, tolerance=1e-5):
    """
    Executes the DebtRank contagion algorithm on the network G.
    
    Parameters:
    - G: nx.DiGraph from network_builder.py
    - damping_factor: Scaling factor (lambda) for shock transmission (default: 0.25)
    - max_iter: Maximum iterations before stopping (default: 20)
    - tolerance: Minimum change in shock levels to declare convergence (default: 1e-5)
    
    Returns:
    - results_df: pd.DataFrame with base and systemic distress probabilities
    """
    logger.info("⚡ STARTING DEBTRANK SYSTEMIC RISK PROPAGATION SIMULATION")
    
    # 1. Initialize shock levels h_i(t)
    # h[i] represents distress level of node i in [0, 1]
    h = {}
    h_prev = {}
    
    for node, data in G.nodes(data=True):
        base_risk = data.get("base_risk", 0.05)
        h[node] = float(base_risk)
        h_prev[node] = 0.0
        
    # Keep copy of initial base risk
    base_risks = h.copy()
    
    # 2. Iterate propagation
    converged = False
    iteration = 0
    
    # Track states for each iteration
    logger.info(f"   • Initializing propagation for {len(h)} nodes...")
    
    while iteration < max_iter and not converged:
        iteration += 1
        h_next = h.copy()
        total_change = 0.0
        
        # In DebtRank, shock propagates from j to i
        # Weight W_ji represents the shock transmitted from j to i.
        # G.edges(data=True) returns (u, v, data) which represents directed edge from u to v.
        # In our network_builder, we added edge from j to i if j's distress impacts i.
        # So u is j (propagator) and v is i (receiver).
        
        # To avoid double-counting and respect original DebtRank, 
        # we compute the increment delta_h_j = h_j(t) - h_prev_j(t-1)
        deltas = {}
        for node in G.nodes():
            deltas[node] = h[node] - h_prev[node]
            
        for u, v, data in G.edges(data=True):
            j = u  # propagator
            i = v  # receiver
            weight = data.get("weight", 0.0)
            
            # Shock contribution from j to i
            delta_j = deltas[j]
            if delta_j > 0:
                h_next[i] += damping_factor * weight * delta_j
                
        # Clip values to [0, 1]
        for node in G.nodes():
            h_next[node] = np.clip(h_next[node], 0.0, 1.0)
            total_change += abs(h_next[node] - h[node])
            
        # Update states
        h_prev = h.copy()
        h = h_next.copy()
        
        logger.info(f"   • Iteration {iteration:02d} | Cumulative shock change: {total_change:.6f}")
        
        if total_change < tolerance:
            converged = True
            logger.info(f"   🎉 DebtRank converged in {iteration} steps.")
            
    if not converged:
        logger.warning(f"   ⚠️ DebtRank reached maximum iterations ({max_iter}) without full convergence.")
        
    # 3. Compile results into DataFrame
    records = []
    for node, data in G.nodes(data=True):
        base_p = base_risks[node]
        sys_p = h[node]
        delta = sys_p - base_p
        
        # Original status
        if base_p >= 0.50:
            base_status = "💥 RED (DANGER)"
        elif base_p >= 0.20:
            base_status = "⚠️ YELLOW (WARNING)"
        else:
            base_status = "✅ GREEN (SAFE)"
            
        # Systemic status after contagion
        if sys_p >= 0.50:
            sys_status = "💥 RED (DANGER)"
        elif sys_p >= 0.25:
            sys_status = "⚠️ YELLOW (WARNING)"
        else:
            sys_status = "✅ GREEN (SAFE)"
            
        records.append({
            "ticker": node,
            "company_name": data.get("name", "N/A"),
            "industry": data.get("industry", "N/A"),
            "exchange": data.get("exchange", "N/A"),
            "base_distress_prob": base_p,
            "systemic_distress_prob": sys_p,
            "risk_delta": delta,
            "base_health_status": base_status,
            "systemic_health_status": sys_status
        })
        
    results_df = pd.DataFrame(records)
    # Sort by systemic risk descending
    results_df = results_df.sort_values(by="systemic_distress_prob", ascending=False).reset_index(drop=True)
    return results_df

def evaluate_systemic_risk(damping_factor=0.25, save_to_csv=True):
    """
    Orchestrates building the network and running the contagion simulation.
    """
    # 1. Build network
    G = build_market_network()
    if not G:
        logger.error("❌ Failed to build network.")
        return None
        
    # 2. Run contagion model
    results_df = run_debtrank_contagion(G, damping_factor=damping_factor)
    
    # 3. Print summary stats
    total = len(results_df)
    red_count = len(results_df[results_df["systemic_health_status"] == "💥 RED (DANGER)"])
    yellow_count = len(results_df[results_df["systemic_health_status"] == "⚠️ YELLOW (WARNING)"])
    green_count = len(results_df[results_df["systemic_health_status"] == "✅ GREEN (SAFE)"])
    
    logger.info("📈 DEBTRANK CONTAGION MODEL - SUMMARY REPORT:")
    logger.info(f"   • Total Audited Companies       : {total}")
    logger.info(f"   • ✅ GREEN (Systemic Safe)      : {green_count} ({green_count/total:.2%})")
    logger.info(f"   • ⚠️ YELLOW (Systemic Warning)   : {yellow_count} ({yellow_count/total:.2%})")
    logger.info(f"   • 💥 RED (Systemic Danger)       : {red_count} ({red_count/total:.2%})")
    
    # Save to CSV
    if save_to_csv:
        import os
        from src.core import config
        output_file = os.path.join(config.DATA_DIR, "systemic_health_report.csv")
        results_df.to_csv(output_file, index=False)
        logger.info(f"💾 Saved systemic health report to: {output_file}")
        
    return results_df

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    results = evaluate_systemic_risk()
    if results is not None:
        print("\nTop 15 Most Systemically Distressed Companies (Base vs. Propagated Risk):")
        print(f"{'Ticker':<6} | {'Company Name':<35} | {'Base Prob':<10} | {'Sys Prob':<10} | {'Delta':<8} | {'Status':<15}")
        print("-" * 100)
        for _, r in results.head(15).iterrows():
            name = r['company_name']
            status = r['systemic_health_status']
            try:
                print(f"{r['ticker']:<6} | {name[:35]:<35} | {r['base_distress_prob']:10.2%} | {r['systemic_distress_prob']:10.2%} | {r['risk_delta']:+8.2%} | {status:<15}")
            except UnicodeEncodeError:
                import unicodedata
                name_clean = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
                # clean emojis from status
                status_clean = status.replace("💥 ", "").replace("⚠️ ", "").replace("✅ ", "")
                print(f"{r['ticker']:<6} | {name_clean[:35]:<35} | {r['base_distress_prob']:10.2%} | {r['systemic_distress_prob']:10.2%} | {r['risk_delta']:+8.2%} | {status_clean:<15}")
