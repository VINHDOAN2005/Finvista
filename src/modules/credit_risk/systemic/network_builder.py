# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: ADAPTIVE NETWORK BUILDER ( toàn sàn )
=================================================
Constructs a directed NetworkX graph of all listed companies (financial & non-financial).
Enriches nodes with XGBoost base distress probability or market-based proxy values.
Establishes directed edges based on Conglomerates, Industry similarity, and Price Correlations.

Author: Antigravity
"""

import os
import json
import pandas as pd
import numpy as np
import networkx as nx
import sqlite3
from src.core.utils import logger
from src.core import config
from src.core.database import engine

# 1. Conglomerate Groups / Ecosystems in Vietnam
CONGLOMERATE_GROUPS = {
    "Vingroup": ["VIC", "VHM", "VRE"],
    "Masan": ["MSN", "MCH", "MML", "MSB", "TCB"],
    "Gelex": ["GEX", "VGC", "IDC", "EIB"],
    "FPT": ["FPT", "FRT", "FTS", "FOX"],
    "Sovico": ["VJC", "HDB"],
    "TTC": ["SBT", "GEG"],
    "Novaland": ["NVL", "PDR"],  # Real estate peers with high correlation
    "KBC_ITA": ["KBC", "ITA"],
    "DauKhi": ["GAS", "PVD", "PVS", "PVT", "BSR", "OIL", "PLX"]
}

def get_conglomerate_map():
    """Maps ticker to conglomerate group name."""
    ticker_map = {}
    for group, tickers in CONGLOMERATE_GROUPS.items():
        for t in tickers:
            ticker_map[t] = group
    return ticker_map

def calculate_stock_volatility_proxies(tickers, days=120):
    """
    Computes annualized historical volatility for tickers using sqlite database history.
    Used as base risk proxy for financial/missing companies.
    """
    if not tickers:
        return {}

    logger.info(f"📈 Calculating market-based volatility proxies for {len(tickers)} financial/missing tickers...")
    vol_map = {}

    try:
        # Load prices from SQLite
        ticker_list_str = "', '".join(tickers)
        query = f"""
            SELECT symbol, date, close 
            FROM stock_history 
            WHERE symbol IN ('{ticker_list_str}') 
            ORDER BY symbol, date ASC
        """
        df = pd.read_sql(query, engine)
        
        if df.empty:
            logger.warning("⚠️ No historical stock price found in database for financial tickers.")
            return {}

        for ticker, group in df.groupby("symbol"):
            group = group.sort_values("date")
            # Calculate daily log returns
            group["log_ret"] = np.log(group["close"] / group["close"].shift(1))
            log_ret = group["log_ret"].dropna()
            
            if len(log_ret) > 5:
                # Annualized volatility
                daily_std = log_ret.std()
                annual_vol = daily_std * np.sqrt(252)
                vol_map[ticker] = annual_vol
            else:
                vol_map[ticker] = 0.25  # Default fallback volatility (25%)
                
    except Exception as e:
        logger.error(f"❌ Error calculating volatility proxies: {e}")
        
    return vol_map

def calculate_price_correlations(tickers, days=120):
    """
    Computes pairwise Pearson correlation matrix for stocks with historical data.
    """
    if not tickers:
        return pd.DataFrame()

    logger.info(f"🔄 Calculating price correlation matrix for {len(tickers)} tickers...")
    try:
        ticker_list_str = "', '".join(tickers)
        query = f"""
            SELECT symbol, date, close 
            FROM stock_history 
            WHERE symbol IN ('{ticker_list_str}') 
            ORDER BY date ASC
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return pd.DataFrame()
            
        # Pivot table to get dates as index and tickers as columns
        pivot_df = df.pivot(index="date", columns="symbol", values="close")
        # Compute daily log returns
        ret_df = np.log(pivot_df / pivot_df.shift(1)).dropna(how="all")
        
        # Keep last 120 trading days
        ret_df = ret_df.tail(days)
        
        # Calculate Pearson correlation matrix
        corr_matrix = ret_df.corr(method="pearson")
        return corr_matrix
    except Exception as e:
        logger.error(f"❌ Error calculating price correlation matrix: {e}")
        return pd.DataFrame()

def build_market_network(beta1=0.4, beta2=0.2, beta3=0.4, correlation_threshold=0.5):
    """
    Builds the directed NetworkX graph representing the Vietnamese stock market contagion network.
    
    Parameters:
    - beta1: Weight for Conglomerate membership link.
    - beta2: Weight for Industry membership link.
    - beta3: Weight for Return Correlation link.
    - correlation_threshold: Minimum correlation coefficient to create an edge.
    
    Returns:
    - G: nx.DiGraph
    """
    logger.info("🕸️ INITIALIZING ADAPTIVE MARKET CONTAGION NETWORK BUILDER")
    
    # 1. Load corporate metadata (all tickers)
    metadata_file = config.COMPANIES_LIST_FILE
    if not os.path.exists(metadata_file):
        logger.error(f"❌ Corporate metadata list not found: {metadata_file}")
        return None
        
    with open(metadata_file, "r", encoding="utf-8") as f:
        companies = json.load(f)
        
    logger.info(f"📂 Loaded {len(companies)} listed companies from metadata.")
    
    # 2. Load ML credit health report (non-financial companies) from SQLite
    ml_risk_map = {}
    try:
        from src.core.database import SessionLocal, CompanyDistressAnalysis
        db = SessionLocal()
        try:
            records = db.query(CompanyDistressAnalysis).all()
            if records:
                df_dist = pd.DataFrame([{
                    "ticker": r.ticker,
                    "year": r.year,
                    "ml_distress_probability": r.distress_probability
                } for r in records])
                latest_recs = df_dist.sort_values('year').groupby('ticker').last().reset_index()
                for _, r in latest_recs.iterrows():
                    ml_risk_map[r["ticker"]] = float(r["ml_distress_probability"] or 0.05)
                logger.info(f"📊 Loaded ML distress probabilities for {len(ml_risk_map)} corporations from SQLite.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Failed to read market health report from SQLite: {e}")
        
    # 3. Separate tickers to identify financial institutions/missing ones
    all_tickers = [c["ticker"] for c in companies]
    missing_tickers = [t for t in all_tickers if t not in ml_risk_map]
    
    # Compute volatility proxies for financial institutions/missing tickers
    vol_proxies = calculate_stock_volatility_proxies(missing_tickers)
    
    # Map conglomerate groups
    conglom_map = get_conglomerate_map()
    
    # 4. Initialize NetworkX Graph
    G = nx.DiGraph()
    
    # 5. Populate nodes with attributes
    # We need market_cap and equity for DebtRank weight scaling
    for c in companies:
        ticker = c["ticker"]
        name = c["company_name"]
        exchange = c["exchange"]
        industry = c["industry"]
        mkt_cap = float(c.get("market_cap", 1e9)) # fallback to 1B VND
        equity = float(c.get("total_equity", mkt_cap * 0.4)) # fallback proxy
        
        # Resolve base risk
        if ticker in ml_risk_map:
            ml_p = ml_risk_map[ticker]
            base_risk = ml_p
            risk_source = "XGBoost (Fundamental)"
        else:
            vol = vol_proxies.get(ticker, 0.25)
            if industry in ["Ngân hàng", "Banking"]:
                base_risk = np.clip(0.02 + 0.3 * vol, 0.01, 0.95)
            elif industry in ["Chứng khoán", "Securities", "Bảo hiểm", "Insurance"]:
                base_risk = np.clip(0.04 + 0.4 * vol, 0.01, 0.95)
            else:
                base_risk = np.clip(0.06 + 0.5 * vol, 0.01, 0.95)
            risk_source = "Volatility Proxy (Structural)"
            
        G.add_node(
            ticker,
            name=name,
            exchange=exchange,
            industry=industry,
            market_cap=mkt_cap,
            equity=equity,
            base_risk=base_risk,
            risk_source=risk_source,
            conglomerate=conglom_map.get(ticker, "None")
        )
        
    logger.info(f"✅ Added {G.number_of_nodes()} nodes to contagion graph.")
    
    # 6. Precompute conglomerate and industry sizes for link scaling
    conglom_mkt_cap = {}
    industry_mkt_cap = {}
    for node, data in G.nodes(data=True):
        cg = data.get("conglomerate", "None")
        ind = data.get("industry", "N/A")
        mc = data.get("market_cap", 0)
        if cg != "None":
            conglom_mkt_cap[cg] = conglom_mkt_cap.get(cg, 0) + mc
        if ind not in ["Khác", "N/A"]:
            industry_mkt_cap[ind] = industry_mkt_cap.get(ind, 0) + mc

    # 7. Calculate Price Correlations
    db_tickers = []
    try:
        db_tickers_df = pd.read_sql("SELECT DISTINCT symbol FROM stock_history", engine)
        db_tickers = db_tickers_df["symbol"].tolist()
    except Exception as e:
        logger.error(f"❌ Error fetching symbols: {e}")
        
    corr_matrix = calculate_price_correlations(db_tickers)
    
    # 8. Establish directed edges and compute weights
    nodes_list = list(G.nodes(data=True))
    num_nodes = len(nodes_list)
    logger.info(f"🕸️ Constructing edges using equity-weighted impact (beta1={beta1}, beta2={beta2}, beta3={beta3})...")
    
    edge_count = 0
    
    for i in range(num_nodes):
        ticker_i, data_i = nodes_list[i]
        industry_i = data_i["industry"]
        conglom_i = data_i["conglomerate"]
        equity_i = data_i["equity"]
        
        for j in range(num_nodes):
            if i == j:
                continue
            ticker_j, data_j = nodes_list[j]
            industry_j = data_j["industry"]
            conglom_j = data_j["conglomerate"]
            mkt_cap_j = data_j["market_cap"]
            
            # DebtRank intuition: Impact from j to i
            # Large j impacts i more. Small equity i is more vulnerable.
            
            # 1. Conglomerate link (Weighted by j's share in conglomerate)
            w_conglom = 0.0
            if conglom_i != "None" and conglom_i == conglom_j:
                total_cg_mc = conglom_mkt_cap.get(conglom_i, 1e12)
                # Influence is j's importance in group
                w_conglom = mkt_cap_j / total_cg_mc
                
            # 2. Industry similarity link (Weighted by industry importance)
            w_industry = 0.0
            if industry_i == industry_j and industry_i not in ["Khác", "N/A"]:
                total_ind_mc = industry_mkt_cap.get(industry_i, 1e12)
                w_industry = mkt_cap_j / total_ind_mc
                
            # 3. Price Correlation link
            w_corr = 0.0
            if not corr_matrix.empty and ticker_i in corr_matrix.index and ticker_j in corr_matrix.columns:
                corr_val = corr_matrix.at[ticker_i, ticker_j]
                if not pd.isna(corr_val) and corr_val > correlation_threshold:
                    w_corr = corr_val * (mkt_cap_j / (mkt_cap_j + equity_i))
            
            # Weighted sum
            weight = beta1 * w_conglom + beta2 * w_industry + beta3 * w_corr
            
            # Edge j -> i (j impacts i)
            if weight > 0.001: # threshold to prune weak links
                G.add_edge(ticker_j, ticker_i, weight=weight)
                edge_count += 1
                
    # 9. Normalize incoming weights for each node (Shock absorption capacity)
    # Total incoming shock from all j cannot exceed 1.0 (paper standard)
    # We use a tighter bound 0.40 to maintain stability in Vietnamese market.
    max_incoming_sum = 0.40
    for node in G.nodes():
        in_edges = list(G.in_edges(node, data=True))
        if not in_edges:
            continue
        total_in_weight = sum(data.get("weight", 0.0) for _, _, data in in_edges)
        if total_in_weight > max_incoming_sum:
            scale = max_incoming_sum / total_in_weight
            for u, v, data in in_edges:
                data["weight"] = data["weight"] * scale
                
    logger.info(f"🕸️ Created {edge_count} directed edges in the network (normalized to max_incoming_sum={max_incoming_sum}).")
    return G

if __name__ == "__main__":
    import sys
    # Initialize logging if run directly
    import logging
    logging.basicConfig(level=logging.INFO)
    G = build_market_network()
    if G:
        print(f"Network built successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        # Print top 5 nodes with highest out-degree/out-weight (most influential risk propagators)
        out_weights = {}
        for u, v, data in G.edges(data=True):
            out_weights[u] = out_weights.get(u, 0) + data['weight']
        sorted_propagators = sorted(out_weights.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\nTop 10 Risk Propagators (Highest cumulative out-edge weights):")
        for ticker, weight in sorted_propagators:
            node_data = G.nodes[ticker]
            name = node_data['name']
            industry = node_data['industry']
            try:
                print(f"  - {ticker:<5} ({name[:30]:<30}) | Industry: {industry:<20} | Out-Weight: {weight:.2f}")
            except UnicodeEncodeError:
                import unicodedata
                name_clean = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
                ind_clean = unicodedata.normalize('NFKD', industry).encode('ascii', 'ignore').decode('ascii')
                print(f"  - {ticker:<5} ({name_clean[:30]:<30}) | Industry: {ind_clean:<20} | Out-Weight: {weight:.2f}")
