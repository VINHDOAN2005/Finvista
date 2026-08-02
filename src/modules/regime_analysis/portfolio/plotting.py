from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np

# Premium Dark Color Palette (Tailwind slate-based)
BG_COLOR = "#0F172A"        # Slate 900
AX_BG_COLOR = "#1E293B"     # Slate 800
TEXT_COLOR = "#F8FAFC"      # Slate 50
TEXT_MUTED = "#94A3B8"      # Slate 400
GRID_COLOR = "#334155"      # Slate 700
BORDER_COLOR = "#334155"    # Slate 700

# Strategy and Asset Colors
COLOR_DYNAMIC = "#38BDF8"   # Tailwind Sky 400
COLOR_STATIC = "#64748B"    # Tailwind Slate 500 (Muted)
COLOR_BULL = "#22C55E"      # Emerald 500
COLOR_SIDEWAYS = "#EAB308"  # Yellow 500
COLOR_BEAR = "#EF4444"      # Red 500

def _style_ax(ax):
    ax.set_facecolor(AX_BG_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.6, linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER_COLOR)
    ax.spines["bottom"].set_color(BORDER_COLOR)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MUTED)
    ax.title.set_color(TEXT_COLOR)
    ax.title.set_fontsize(12)
    ax.title.set_weight("bold")


def plot_regimes(index: pd.DatetimeIndex, labels: pd.Series, save_path: str):
    fig, ax = plt.subplots(figsize=(12, 3))
    fig.patch.set_facecolor(BG_COLOR)
    _style_ax(ax)

    unique = sorted(labels.unique())
    regime_names = {
        0: "Bullish (Low Vol)",
        1: "Bullish (High Vol)",
        2: "Bearish (Low Vol)",
        3: "Bearish (High Vol)"
    }
    colors = {
        0: COLOR_BULL,
        1: COLOR_SIDEWAYS,
        2: "#6366F1",  # Indigo
        3: COLOR_BEAR
    }

    for k in unique:
        mask = labels.values == k
        ax.fill_between(
            index, 0, 1,
            where=mask,
            transform=ax.get_xaxis_transform(),
            alpha=0.15,
            color=colors.get(k, "#64748B"),
            label=regime_names.get(k, f"Regime {k}")
        )

    ax.set_title("Detected Market Regimes (Aligned HMM Viterbi Path)", fontsize=12, fontweight="bold", pad=10)
    ax.set_yticks([])
    ax.legend(loc="upper left", fontsize=9, framealpha=0.8, facecolor=AX_BG_COLOR, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()


def plot_equity_curves(eq_dyn: pd.Series, eq_static: pd.Series, save_path: str):
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(BG_COLOR)
    _style_ax(ax)

    ax.plot(eq_dyn.index, eq_dyn.values, color=COLOR_DYNAMIC, linewidth=2.0, label="Dynamic (Regime-Switching)")
    ax.plot(eq_static.index, eq_static.values, color=COLOR_STATIC, linewidth=1.5, linestyle="--", label="Static Baseline (Full Sample)")

    ax.set_title("Portfolio Equity Curve Comparison", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Portfolio Value (Normalised to 1.0)", fontsize=10)
    ax.set_xlabel("")
    ax.legend(fontsize=10, framealpha=0.9, loc="upper left", facecolor=AX_BG_COLOR, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR)

    # Performance summary annotation on plot
    dyn_sharpe = _quick_sharpe(eq_dyn)
    sta_sharpe = _quick_sharpe(eq_static)
    dyn_dd = _quick_mdd(eq_dyn)
    sta_dd = _quick_mdd(eq_static)
    
    text = (
        f"Dynamic: Sharpe={dyn_sharpe:.3f}, MaxDD={dyn_dd*100:.1f}%\n"
        f"Static:     Sharpe={sta_sharpe:.3f}, MaxDD={sta_dd*100:.1f}%"
    )
    ax.annotate(
        text,
        xy=(0.02, 0.82), xycoords="axes fraction",
        fontsize=9, color=TEXT_COLOR, va="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=AX_BG_COLOR, edgecolor=BORDER_COLOR, alpha=0.9)
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()


def plot_weights(weights_hist: pd.DataFrame, save_path: str):
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(BG_COLOR)
    _style_ax(ax)

    # Tailwind-inspired vibrant palette for stacked area
    colors = ["#38BDF8", "#34D399", "#FBBF24", "#F87171", "#C084FC", "#F472B6"]
    
    # Render stacked area plot for portfolio weights
    ax.stackplot(
        weights_hist.index,
        [weights_hist[col].values for col in weights_hist.columns],
        labels=weights_hist.columns,
        colors=colors[:len(weights_hist.columns)],
        alpha=0.8
    )

    ax.set_title("Dynamic Portfolio Weight Allocation Over Time", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Portfolio Weight", fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.legend(ncol=len(weights_hist.columns), fontsize=9, framealpha=0.9, loc="upper left", facecolor=AX_BG_COLOR, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()


def _quick_sharpe(equity: pd.Series) -> float:
    r = equity.pct_change().dropna().values
    if r.std() == 0:
        return 0.0
    return float(np.sqrt(252) * r.mean() / r.std())


def _quick_mdd(equity: pd.Series) -> float:
    x = equity.values
    roll_max = np.maximum.accumulate(x)
    dd = x / roll_max - 1.0
    return float(np.nanmin(dd))