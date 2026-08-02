# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: VN-INDEX REGIME DETECTOR AUDIT TOOL v4.0
=====================================================
Trains a 4-state Hybrid HMM (2-state HMM × SMA-50 Trend) on VN-Index.
Generates a clean, presentation-grade visualization.

Author: Antigravity
Version: 4.0 (Clean Presentation Style)
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
from vnstock import Market
from datetime import datetime, timedelta

if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.makedirs("results", exist_ok=True)

# ─────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────
BG      = '#0d1117'   # near-black
PANEL   = '#161b22'   # dark panel
BORDER  = '#30363d'   # subtle border
TEXT    = '#e6edf3'
MUTED   = '#8b949e'

# 4 regime palette – high contrast against dark bg
C = {
    0: '#3fb950',   # Bullish Low-Vol  → bright green
    1: '#e3b341',   # Bullish High-Vol → amber
    2: '#58a6ff',   # Bearish Low-Vol  → bright blue
    3: '#f85149',   # Bearish Crisis   → red
}
LABEL = {
    0: 'Bullish (Low Vol)',
    1: 'Bullish (High Vol)',
    2: 'Bearish (Low Vol)',
    3: 'Bearish Crisis (High Vol)',
}
BG_ALPHA = {0: 0.15, 1: 0.20, 2: 0.20, 3: 0.25}


def _smooth(arr: np.ndarray, min_run: int = 4) -> np.ndarray:
    """Merge regime runs shorter than min_run into the previous regime."""
    s = arr.copy()
    for _ in range(10):
        changed = False
        i = 0
        while i < len(s):
            k = s[i]; j = i
            while j < len(s) and s[j] == k:
                j += 1
            if (j - i) < min_run and i > 0:
                s[i:j] = s[i - 1]
                changed = True
            i = j
        if not changed:
            break
    return s


def _setup_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.spines[:].set_color(BORDER)
    ax.grid(axis='both', color=BORDER, linestyle='--', linewidth=0.6, alpha=0.6)


import argparse
def run_regime_audit(symbol: str = 'VNINDEX', days: int = 1250):
    print(f"🚀 Starting {symbol} HMM Regime Audit...")
    end_date   = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    df = pd.DataFrame()
    if symbol == 'VNINDEX':
        try:
            market = Market()
            idx    = market.index(symbol='VNINDEX')
            df     = idx.ohlcv(start=start_date, end=end_date, resolution='1D', count=days)
        except Exception as e:
            print(f"❌ {e}"); sys.exit(1)
    else:
        try:
            import sqlite3
            conn = sqlite3.connect('data/finvista.db')
            query = f"SELECT date, close, volume FROM stock_history WHERE symbol = '{symbol}' AND date >= '{start_date}' AND date <= '{end_date}' ORDER BY date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
            # If data missing, try yfinance
            if df.empty:
                import yfinance as yf
                df = yf.download(symbol, start=start_date, end=end_date, progress=False)
                df = df.reset_index()
                df = df.rename(columns={'Date': 'date', 'Close': 'close', 'Volume': 'volume'})
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f"❌ {e}"); sys.exit(1)

    if df.empty or len(df) < 100:
        print("❌ Data too short."); sys.exit(1)

    tc = 'time' if 'time' in df.columns else 'date'
    df = df.sort_values(tc).reset_index(drop=True)
    df['date'] = pd.to_datetime(df[tc])
    print(f"📊 {len(df)} sessions  {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")

    # ── Features ──────────────────────────────────────────────
    from src.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features
    df = prepare_vnindex_features(df)
    
    # Map back standard names for the legacy plot code
    df['log_ret'] = df['log_return']
    df['vol20'] = df['rolling_vol']
    df['log_vrat'] = df['log_volume_ratio']

    # ── 4-State Hybrid HMM ──────────────────────────────────
    print("⚙️  Fitting 4-State Hybrid HMM...")
    from src.modules.regime_analysis.portfolio.regime_model import fit_vnindex_hmm
    hybrid_model, _ = fit_vnindex_hmm(df)
    
    hmm_states = hybrid_model.predict(df)
    hmm_probs  = hybrid_model.predict_proba(df)
    
    # Use Hybrid HMM states directly
    states = hmm_states
    cprobs = hmm_probs
    smooth_states = _smooth(states, min_run=4)

    # ── Stats ─────────────────────────────────────────────────
    print("\n" + "="*78)
    print("📈 4-STATE GAUSSIAN HMM REGIME STATISTICS (aligned by Mean Return)")
    print("="*78)
    print(f"{'REGIME':<32} {'N':>5} {'PCT':>6} {'MEAN/D':>9} {'ANN VOL':>9} {'SHARPE':>7}")
    print("-"*78)
    for k in range(4):
        m = states == k
        if not m.any(): continue
        r   = df.loc[m, 'log_ret']
        n   = m.sum()
        mu  = r.mean()
        vol = r.std() * np.sqrt(252)
        ann = (1 + mu)**252 - 1
        sh  = ann / vol if vol > 0 else 0
        print(f"{LABEL[k]:<32} {n:>5} {n/len(df):>6.1%} {mu:>9.4%} {vol:>9.2%} {sh:>7.2f}")
    print("="*78)
    print("\n🔄 HMM TRANSITION MATRIX:")
    for i in range(4):
        row = " | ".join(f"S{j}: {hybrid_model.transmat_[i, j]:.1%}" for j in range(4))
        print(f"  Từ State {i}: [ {row} ]")

    # ══════════════════════════════════════════════════════════
    # CHART
    # ══════════════════════════════════════════════════════════
    print("\n🎨 Rendering chart...")
    plt.rcParams.update({
        'figure.facecolor': BG, 'savefig.facecolor': BG,
        'text.color': TEXT, 'font.family': 'DejaVu Sans',
    })

    fig = plt.figure(figsize=(18, 12), dpi=150)
    gs  = gridspec.GridSpec(3, 1, figure=fig,
                            height_ratios=[3, 1.2, 1],
                            hspace=0.05,
                            top=0.93, bottom=0.07, left=0.06, right=0.97)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    for ax in (ax1, ax2, ax3):
        _setup_ax(ax)

    dates  = df['date']
    prices = df['close'].values

    # ── Panel 1 : Price + regime shading ──────────────────────
    # Shade background by smoothed regime
    for k in range(4):
        col = C[k]; alpha = BG_ALPHA[k]
        i = 0
        while i < len(smooth_states):
            if smooth_states[i] == k:
                j = i
                while j < len(smooth_states) and smooth_states[j] == k:
                    j += 1
                ax1.axvspan(dates.iloc[i], dates.iloc[j-1],
                            color=col, alpha=alpha, linewidth=0, zorder=1)
                i = j
            else:
                i += 1

    # Colored price line (raw states for precision)
    xn     = mdates.date2num(dates)
    pts    = np.array([xn, prices]).T.reshape(-1, 1, 2)
    segs   = np.concatenate([pts[:-1], pts[1:]], axis=1)
    cols   = [C[smooth_states[i]] for i in range(len(segs))]
    lc     = LineCollection(segs, colors=cols, linewidths=2.0, zorder=3)
    ax1.add_collection(lc)

    # KAMA
    ax1.plot(dates, df['kama'], color=MUTED, lw=1.0,
             ls='--', alpha=0.6, label='KAMA', zorder=2)

    ax1.set_xlim(dates.iloc[0], dates.iloc[-1])
    ax1.set_ylim(prices.min() * 0.97, prices.max() * 1.03)
    ax1.set_ylabel(f"{symbol} Price", color=TEXT, fontsize=12)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # Regime legend (colored patches)
    handles = [mpatches.Patch(facecolor=C[k], alpha=0.9, label=LABEL[k]) for k in range(4)]
    handles += [plt.Line2D([0],[0], color=MUTED, ls='--', lw=1.0, label='SMA-50')]
    ax1.legend(handles=handles, loc='upper left',
               framealpha=0.8, facecolor='#21262d',
               edgecolor=BORDER, fontsize=9, ncol=2)

    # Stats annotation (top-right)
    stats_lines = []
    for k in range(4):
        m  = states == k
        if not m.any(): continue
        sh = ((1 + df.loc[m,'log_ret'].mean())**252 - 1) / (df.loc[m,'log_ret'].std()*np.sqrt(252))
        pct = m.sum() / len(df)
        stats_lines.append(f"{LABEL[k][:20]:<20}  {pct:>5.1%}   Sharpe {sh:>+.2f}")
    ax1.text(0.99, 0.98, "\n".join(stats_lines),
             transform=ax1.transAxes, ha='right', va='top',
             fontsize=8, family='monospace', color=TEXT,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#21262d',
                       edgecolor=BORDER, alpha=0.85))

    # Title
    fig.suptitle(f"FINVISTA · {symbol} Market Regime Detection\n"
                 "Hybrid Model: 2-State Gaussian HMM  ×  KAMA Trend Filter",
                 fontsize=14, fontweight='bold', color=TEXT, y=0.98)

    # ── Panel 2 : Smoothed Regime Probability bars ────────────
    # Smooth probs with rolling mean to reduce noise
    window = 5
    sp = pd.DataFrame(cprobs).rolling(window, min_periods=1, center=True).mean().values

    ax2.stackplot(dates,
                  sp[:,0], sp[:,1], sp[:,2], sp[:,3],
                  colors=[C[k] for k in range(4)],
                  alpha=0.82)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0, 0.5, 1.0])
    ax2.set_yticklabels(['0%', '50%', '100%'], fontsize=8, color=MUTED)
    ax2.set_ylabel("Regime\nProb.", color=TEXT, fontsize=10)
    plt.setp(ax2.get_xticklabels(), visible=False)

    # ── Panel 3 : Rolling Volatility ──────────────────────────
    vol_smooth = df['vol20'].rolling(5, min_periods=1).mean()
    ax3.fill_between(dates, vol_smooth, color='#e3b341', alpha=0.22)
    ax3.plot(dates, vol_smooth, color='#e3b341', lw=1.5,
             label='20-Day Annualised Volatility (smoothed)')

    # Shade crisis spikes (vol > 30%)
    ax3.fill_between(dates, vol_smooth, 0.30,
                     where=vol_smooth > 0.30,
                     color=C[3], alpha=0.35, label='Crisis threshold (30%)')
    ax3.axhline(0.30, color=C[3], lw=0.8, ls=':', alpha=0.7)

    ax3.set_ylabel("Ann. Vol", color=TEXT, fontsize=10)
    ax3.set_xlabel("Date", color=MUTED, fontsize=10)
    ax3.legend(loc='upper right', fontsize=8,
               facecolor='#21262d', edgecolor=BORDER, framealpha=0.8)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=30, ha='right',
             fontsize=8, color=MUTED)

    out = f"results/{symbol.lower()}_regime_audit.png"
    fig.savefig(out, facecolor=BG, edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"✅  Saved → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default='VNINDEX', help='Symbol to audit')
    parser.add_argument('--days', type=int, default=1250, help='Days of history to fetch')
    args = parser.parse_args()
    run_regime_audit(symbol=args.symbol, days=args.days)
