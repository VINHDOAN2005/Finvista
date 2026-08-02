# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HOSE-COMPLIANT QUANTITATIVE PAPER TRADING ENGINE
============================================================
Enforces real-world Vietnamese Covered Warrant trading regulations:
  1. Transaction Costs: 0.15% Buying Fee, 0.25% Selling Fee & Tax.
  2. Lot Size constraints: HOSE lot minimum is 100 CWs (multiples of 100).
  3. Settlement constraints: T+2.5 settlement lock (locked until T+2 afternoon).
  4. Maturity Risk Management: Hard cut-off to sell when days-to-maturity < 10 days to avoid Theta decay.
  5. Position sizing: Max 20% capital allocation per CW.
  6. Strategy: Volatility Arbitrage (buy CHEAP, sell on SL/TP or EXPENSIVE).

Author: samvo
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from src.core import config
from src.modules.regime_analysis.indicators.garch_evt_var import get_underlying_garch_evt_var, get_conformal_calibrated_var
from src.modules.cw_pricing.models.pricing_core import calculate_merton_jump_diffusion_price

# Default file paths
PORTFOLIO_FILE = os.path.join("data", "config", "paper_portfolio.json")
REPORT_PATH = os.path.join("data", "processed", "excel_cw_report.csv")

# Trading constants
INITIAL_CASH = 100_000_000.0  # 100 Million VND
BUY_FEE_RATE = 0.0015         # 0.15%
SELL_FEE_RATE = 0.0025        # 0.15% fee + 0.1% tax = 0.25%
HOSE_LOT_SIZE = 100           # Minimum trading lot
MAX_ALLOCATION_PCT = 0.20     # Max 20% of total portfolio value per position

# Strategy thresholds (VN-QUANT V5.3 Adaptive)
V51_TAKE_PROFIT_PCT = 0.50     # V5.1 Momentum TP
V52_TAKE_PROFIT_PCT = 0.15     # V5.2 Defensive TP
STOP_LOSS_PCT = -0.20         # Base SL
MATURITY_LIMIT_DAYS = 10      # Exit position if < 10 days left to maturity

def load_portfolio(username: str = "demo") -> dict:
    """Load or initialize the paper trading portfolio using the SQL database."""
    from src.core.database import SessionLocal, User, Portfolio, Position, TransactionHistory
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # Check if this is demo, fallback to init_db
            if username == "demo":
                from src.core.database import init_db
                init_db()
                user = db.query(User).filter(User.username == "demo").first()
            else:
                # Dynamically register custom user with standard safe fallback hash
                user = User(username=username, hashed_password="pbkdf2_sha256$30000$dynamic_user$hash")
                db.add(user)
                db.commit()
                db.refresh(user)
                
        # Resolve portfolio balance
        port = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
        if not port:
            port = Portfolio(user_id=user.id, cash=INITIAL_CASH, initial_cash=INITIAL_CASH)
            db.add(port)
            db.commit()
            db.refresh(port)
            
        # Resolve positions
        db_positions = db.query(Position).filter(Position.user_id == user.id).all()
        positions_dict = {}
        for pos in db_positions:
            positions_dict[pos.symbol] = {
                "symbol": pos.symbol,
                "underlying": pos.underlying,
                "qty": pos.qty,
                "buy_price": pos.buy_price,
                "buy_date": pos.buy_date,
                "settlement_date": pos.settlement_date,
                "total_cost": pos.total_cost,
                "score_at_buy": pos.score_at_buy,
                "days_at_buy": pos.days_at_buy
            }
            
        # Resolve history
        db_history = db.query(TransactionHistory).filter(TransactionHistory.user_id == user.id).all()
        history_list = []
        for tx in db_history:
            history_list.append({
                "symbol": tx.symbol,
                "underlying": tx.underlying,
                "type": tx.type,
                "qty": tx.qty,
                "price": tx.price,
                "value": tx.value,
                "fee": tx.fee,
                "date": tx.date,
                "reason": tx.reason
            })
            
        return {
            "cash": port.cash,
            "initial_cash": port.initial_cash,
            "positions": positions_dict,
            "history": history_list
        }
    except Exception as e:
        print(f"⚠️ SQLite portfolio fallback triggered: {e}")
        # Local JSON file fallback in case database becomes locked or unavailable
        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "cash": INITIAL_CASH,
            "initial_cash": INITIAL_CASH,
            "positions": {},
            "history": []
        }
    finally:
        db.close()

def save_portfolio(portfolio: dict, username: str = "demo"):
    """Persist the portfolio state to both SQL Database and JSON backup."""
    # Write to local JSON file for backup (only for demo to keep workspace clean)
    if username == "demo":
        try:
            os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
            with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
                json.dump(portfolio, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        
    from src.core.database import SessionLocal, User, Portfolio, Position, TransactionHistory
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return
            
        # 1. Update Portfolio Cash
        port = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
        if not port:
            port = Portfolio(user_id=user.id)
            db.add(port)
        port.cash = portfolio.get("cash", INITIAL_CASH)
        port.initial_cash = portfolio.get("initial_cash", INITIAL_CASH)
        
        # 2. Sync Positions (delete obsolete ones, insert/update current ones)
        db.query(Position).filter(Position.user_id == user.id).delete()
        for sym, pos in portfolio.get("positions", {}).items():
            db_pos = Position(
                user_id=user.id,
                symbol=sym,
                underlying=pos.get("underlying"),
                qty=pos["qty"],
                buy_price=pos["buy_price"],
                buy_date=pos["buy_date"],
                settlement_date=pos["settlement_date"],
                total_cost=pos["total_cost"],
                score_at_buy=pos.get("score_at_buy"),
                days_at_buy=pos.get("days_at_buy")
            )
            db.add(db_pos)
            
        # 3. Sync Transactions
        db.query(TransactionHistory).filter(TransactionHistory.user_id == user.id).delete()
        for tx in portfolio.get("history", []):
            db_tx = TransactionHistory(
                user_id=user.id,
                symbol=tx["symbol"],
                underlying=tx.get("underlying"),
                type=tx["type"],
                qty=tx["qty"],
                price=tx["price"],
                value=tx["value"],
                fee=tx["fee"],
                date=tx["date"],
                reason=tx.get("reason")
            )
            db.add(db_tx)
            
        log_nav_checkpoint(db, user.id)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ SQLite save error: {e}")
    finally:
        db.close()

def log_nav_checkpoint(db, user_id: int):
    """Logs a new NAV checkpoint in SQLite for charting."""
    from src.core.database import Portfolio, Position, MarketOpportunity, PortfolioNavHistory
    port = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not port:
        return
    
    positions = db.query(Position).filter(Position.user_id == user_id).all()
    opportunities = db.query(MarketOpportunity).all()
    live_prices = {opp.symbol: opp.price for opp in opportunities}
    
    pos_val = 0.0
    for pos in positions:
        curr_price = live_prices.get(pos.symbol, pos.buy_price)
        pos_val += pos.qty * curr_price
        
    total_nav = port.cash + pos_val
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    checkpoint = PortfolioNavHistory(
        user_id=user_id,
        total_nav=total_nav,
        cash=port.cash,
        positions_value=pos_val,
        date=date_str
    )
    db.add(checkpoint)

def reset_portfolio(username: str = "demo") -> dict:
    """Reset the paper trading account to initial state in both SQL and Backup."""
    portfolio = {
        "cash": INITIAL_CASH,
        "initial_cash": INITIAL_CASH,
        "positions": {},
        "history": []
    }
    save_portfolio(portfolio, username=username)
    return portfolio

def is_market_open() -> bool:
    """Check if HOSE market is currently open for trading (Mon-Fri, 9:00-11:30 and 13:00-14:45)."""
    now = datetime.now()
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    time_str = now.strftime("%H:%M:%S")
    in_morning = "09:00:00" <= time_str <= "11:30:00"
    in_afternoon = "13:00:00" <= time_str <= "14:45:00"
    return in_morning or in_afternoon

def calculate_settlement_date(buy_date_str: str) -> str:
    """
    Calculate T+2.5 settlement date.
    Warrants bought on Day T are available to be sold on afternoon of T+2 (at 13:00).
    Excludes weekends.
    """
    buy_dt = datetime.fromisoformat(buy_date_str)
    days_added = 0
    curr_dt = buy_dt
    while days_added < 2:
        curr_dt += timedelta(days=1)
        if curr_dt.weekday() < 5:  # Monday to Friday
            days_added += 1
            
    # Set to 13:00:00 on the T+2 business day
    settlement_dt = datetime(curr_dt.year, curr_dt.month, curr_dt.day, 13, 0, 0)
    return settlement_dt.isoformat()

def get_portfolio_value(portfolio: dict, live_prices: dict) -> float:
    """Calculate the total current net asset value (NAV) of the portfolio."""
    pos_val = 0.0
    for symbol, pos in portfolio["positions"].items():
        price = live_prices.get(symbol, pos["buy_price"])
        pos_val += pos["qty"] * price
    return portfolio["cash"] + pos_val

def execute_buy(symbol: str, underlying: str, price: float, score: float, days_left: int, username: str = "demo", mkt_regime: dict = None) -> dict:
    """Execute a HOSE-compliant BUY order with VN-QUANT V5.3 Institutional Strict Filters & Slippage."""
    portfolio = load_portfolio(username=username)
    
    if price <= 0:
        return {"status": "error", "message": f"❌ Invalid market price {price}đ for {symbol}."}
        
    # Check if we already hold this position
    if symbol in portfolio["positions"]:
        return {"status": "error", "message": f"⚠️ Already holding position in {symbol}."}
        
    # ── Institutional Filter: Optimal Lifespan ──
    # Note: MIN/MAX_MATURITY_ENTRY constants assumed or imported from config
    MIN_MATURITY_ENTRY = 20
    MAX_MATURITY_ENTRY = 150
    if days_left < MIN_MATURITY_ENTRY or days_left > MAX_MATURITY_ENTRY:
        return {"status": "error", "message": f"⏩ Skipping {symbol} (Days to maturity {days_left} outside optimal window {MIN_MATURITY_ENTRY}-{MAX_MATURITY_ENTRY})."}

    # ── Liquidity, ITM, & Distress Gates ─────────────────────────────
    adv10 = 0.0
    volume_today = 0.0
    distress_prob = 0.10
    strike_price = 0.0
    underlying_price = 0.0
    raw_iv = 0.40
    hv30 = 0.35
    prob_itm = 0.5 # Default
    
    try:
        from src.core.database import SessionLocal, CWHistoricalPrice
        db = SessionLocal()
        try:
            records = (
                db.query(CWHistoricalPrice)
                .filter(CWHistoricalPrice.symbol == symbol)
                .order_by(CWHistoricalPrice.date.desc())
                .limit(10)
                .all()
            )
            if len(records) > 0:
                adv10 = sum(r.volume for r in records) / len(records)
        finally:
            db.close()

        # Load market data from DB
        try:
            from src.modules.cw_pricing.backtest.reporter import load_opportunities_from_db
            df_rep = load_opportunities_from_db(fallback_to_csv=True)
            if not df_rep.empty:
                match = df_rep[df_rep["A_MaCW"] == symbol]
                if not match.empty:
                    volume_today = float(match.get("D_Volume", pd.Series([0.0])).iloc[0])
                    distress_prob = float(match.get("underlying_distress_prob", pd.Series([0.1])).iloc[0])
                    strike_price = float(match.get("R_Strike", pd.Series([0.0])).iloc[0])
                    underlying_price = float(match.get("hidden_underlying_price", pd.Series([0.0])).iloc[0])
                    raw_iv = float(match.get("S_IV_Pct", pd.Series([40.0])).iloc[0]) / 100.0
                    hv30 = float(match.get("S_HV_Pct", pd.Series([35.0])).iloc[0]) / 100.0
                    prob_itm = float(match.get("prob_itm", pd.Series([0.5])).iloc[0])
        except Exception as e:
            print(f"⚠️ Warning loading market data from DB for {symbol}: {e}")

    except Exception as e:
        print(f"⚠️ Warning loading metrics for {symbol}: {e}")

    # ── Institutional Filter: Liquidity Gate ──
    MIN_LIQUIDITY_VOL = 100000
    effective_vol = adv10 if adv10 > 0 else volume_today
    if effective_vol < MIN_LIQUIDITY_VOL:
        return {"status": "error", "message": f"❌ Rejected {symbol} (Volume {effective_vol:,.0f} < 100k limit)."}

    # ── Institutional Filter: ITM Only (Stock > Strike) ──
    if strike_price > 0 and underlying_price > 0 and underlying_price <= strike_price:
        return {"status": "error", "message": f"❌ Rejected {symbol} (OTM Filter: Stock {underlying_price:,.0f} <= Strike {strike_price:,.0f})."}
        
    # ── Institutional Filter: Volatility Arbitrage (IV < HV) ──
    if raw_iv >= hv30 * 1.1: # Allow a small buffer
         return {"status": "error", "message": f"❌ Rejected {symbol} (Vol-Arb Filter: IV {raw_iv*100:.1f}% >= HV {hv30*100:.1f}%)."}

    # ── V5.4 DYNAMIC KELLY-LITE SIZING ──────────────────────────────
    total_nav = get_portfolio_value(portfolio, {symbol: price})
    
    # Kelly-lite: scale by ITM probability and regime
    # Base allocation 10%, scaled by (2 * prob_itm - 1) clipped to [0.5, 1.5]
    kelly_factor = max(0.5, min(1.5, 2.0 * prob_itm))
    
    is_momentum_regime = False
    if mkt_regime:
        is_momentum_regime = mkt_regime["regime"] in ["BULLISH_VOL_CONTRACTION", "BULLISH_VOL_EXPANSION"]
    
    base_alloc = 0.12 if is_momentum_regime else 0.06
    alloc_pct = base_alloc * kelly_factor
    
    # Scale down if elevated distress risk
    if distress_prob > 0.30:
        alloc_pct *= 0.5
        
    # Max allocation per CW
    alloc_pct = min(alloc_pct, MAX_ALLOCATION_PCT)
    
    max_alloc_value = total_nav * alloc_pct
    target_purchase_val = min(max_alloc_value, portfolio["cash"])
    
    raw_qty = target_purchase_val / (price * (1 + BUY_FEE_RATE))
    qty = int(raw_qty // HOSE_LOT_SIZE) * HOSE_LOT_SIZE
    
    if qty <= 0:
        return {"status": "error", "message": f"❌ Cash limit too low for {symbol}."}

    # ── REAL-TIME SLIPPAGE CALCULATION ──────────────────────────────
    from src.infra.orderbook_scraper import get_real_order_book, calculate_slippage
    ob = get_real_order_book(symbol)
    execution_price = price
    slippage_note = ""
    
    if ob:
        slip_res = calculate_slippage(ob, "BUY", qty)
        if "error" not in slip_res:
            execution_price = slip_res["avg_price"]
            slippage_pct = slip_res["slippage_pct"]
            if slippage_pct > 1.5:
                return {"status": "error", "message": f"❌ Order Rejected: Estimated slippage too high ({slippage_pct:.2f}%)."}
            slippage_note = f" (Slippage: {slippage_pct:.2f}%)"
        
    gross_value = qty * execution_price
    fee = gross_value * BUY_FEE_RATE
    total_cost = gross_value + fee
    
    if total_cost > portfolio["cash"]:
        # Recalculate if slippage pushed cost over cash
        qty = int((portfolio["cash"] / (execution_price * (1 + BUY_FEE_RATE))) // HOSE_LOT_SIZE) * HOSE_LOT_SIZE
        gross_value = qty * execution_price
        fee = gross_value * BUY_FEE_RATE
        total_cost = gross_value + fee
        if qty <= 0: return {"status": "error", "message": f"❌ Insufficient cash after slippage adjustment."}

    # Execute
    portfolio["cash"] -= total_cost
    now_str = datetime.now().isoformat()
    portfolio["positions"][symbol] = {
        "symbol": symbol,
        "underlying": underlying,
        "qty": qty,
        "buy_price": execution_price,
        "buy_date": now_str,
        "settlement_date": calculate_settlement_date(now_str),
        "total_cost": total_cost,
        "score_at_buy": score,
        "days_at_buy": days_left
    }
    portfolio["history"].append({
        "symbol": symbol,
        "underlying": underlying,
        "type": "BUY",
        "qty": qty,
        "price": execution_price,
        "value": gross_value,
        "fee": fee,
        "date": now_str,
        "reason": f"V5.4 Dynamic Sizing | Kelly-Lite {kelly_factor:.2f}x{slippage_note}"
    })
    
    save_portfolio(portfolio, username=username)
    return {
        "status": "success",
        "message": f"🛍️ BOUGHT {qty:,} {symbol} at {execution_price:,.0f}đ{slippage_note}"
    }


def execute_sell(symbol: str, price: float, reason: str, username: str = "demo") -> dict:
    """Execute a HOSE-compliant SELL order with slippage and T+2.5 checks."""
    portfolio = load_portfolio(username=username)
    
    if symbol not in portfolio["positions"]:
        return {"status": "error", "message": f"❌ No position held in {symbol}."}
        
    pos = portfolio["positions"][symbol]
    qty = pos["qty"]
    
    # T+2.5 Settlement lock check
    now = datetime.now()
    settlement_dt = datetime.fromisoformat(pos["settlement_date"])
    if now < settlement_dt:
        time_left = settlement_dt - now
        hours_left = time_left.total_seconds() / 3600.0
        return {
            "status": "error", 
            "message": f"🔒 Position in {symbol} is locked in T+2.5 settlement cycle! Available in {hours_left:.1f}h."
        }
        
    # ── REAL-TIME SLIPPAGE CALCULATION ──────────────────────────────
    from src.infra.orderbook_scraper import get_real_order_book, calculate_slippage
    ob = get_real_order_book(symbol)
    execution_price = price
    slippage_note = ""
    
    if ob:
        slip_res = calculate_slippage(ob, "SELL", qty)
        if "error" not in slip_res:
            execution_price = slip_res["avg_price"]
            slippage_pct = slip_res["slippage_pct"]
            slippage_note = f" (Slippage: {slippage_pct:.2f}%)"

    # Calculate proceeds
    gross_value = qty * execution_price
    fee_and_tax = gross_value * SELL_FEE_RATE
    net_proceeds = gross_value - fee_and_tax
    
    # Add cash
    portfolio["cash"] += net_proceeds
    
    # Remove position
    portfolio["positions"].pop(symbol)
    
    # Add to history
    portfolio["history"].append({
        "symbol": symbol,
        "underlying": pos["underlying"],
        "type": "SELL",
        "qty": qty,
        "price": execution_price,
        "value": gross_value,
        "fee": fee_and_tax,
        "date": now.isoformat(),
        "reason": f"{reason}{slippage_note}",
        "buy_price": pos["buy_price"],
        "p_l_vnd": net_proceeds - pos["total_cost"],
        "p_l_pct": (execution_price - pos["buy_price"]) / pos["buy_price"] * 100
    })
    
    save_portfolio(portfolio, username=username)
    p_l = net_proceeds - pos["total_cost"]
    p_l_pct = (execution_price - pos["buy_price"]) / pos["buy_price"] * 100
    
    sign = "+" if p_l >= 0 else ""
    return {
        "status": "success",
        "message": f"💸 SOLD {qty:,} {symbol} at {execution_price:,.0f}đ | P/L: {sign}{p_l:,.0f}đ ({sign}{p_l_pct:.2f}%){slippage_note}"
    }

def get_underlying_technical_metrics(underlying: str) -> dict:
    """
    Fetch last 40 daily price records for the underlying stock.
    Calculate EMA15, ATR14 and ATRr14.
    """
    from src.core.database import engine
    import pandas as pd
    try:
        query = f"""
            SELECT date, close, high, low 
            FROM stock_history 
            WHERE symbol = '{underlying}' 
            ORDER BY date DESC 
            LIMIT 40
        """
        df_stock = pd.read_sql(query, engine)
        if df_stock.empty or len(df_stock) < 20:
            return {"ema15": None, "atrr14": 0.025, "latest_close": None}
            
        # Reverse to chronological order
        df_stock = df_stock.iloc[::-1].reset_index(drop=True)
        df_stock['close'] = df_stock['close'].astype(float)
        df_stock['high'] = df_stock['high'].astype(float)
        df_stock['low'] = df_stock['low'].astype(float)
        
        # Calculate EMA15
        df_stock['EMA15'] = df_stock['close'].ewm(span=15, adjust=False).mean()
        
        # Calculate ATR14
        high_low = df_stock['high'] - df_stock['low']
        high_close = (df_stock['high'] - df_stock['close'].shift()).abs()
        low_close = (df_stock['low'] - df_stock['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df_stock['ATR14'] = tr.rolling(14).mean()
        df_stock['ATRr14'] = df_stock['ATR14'] / df_stock['close']
        
        latest = df_stock.iloc[-1]
        return {
            "ema15": float(latest['EMA15']) if pd.notna(latest['EMA15']) else None,
            "atrr14": float(latest['ATRr14']) if pd.notna(latest['ATRr14']) else 0.025,
            "latest_close": float(latest['close']) if pd.notna(latest['close']) else None
        }
    except Exception as e:
        print(f"⚠️ Warning fetching underlying technical metrics for {underlying}: {e}")
        return {"ema15": None, "atrr14": 0.025, "latest_close": None}

def get_peak_price_since_buy(symbol: str, buy_date_str: str, buy_price: float) -> float:
    """Get the highest recorded price of the warrant since the purchase date."""
    from src.core.database import engine
    import pandas as pd
    try:
        # Extract date from buy_date_str (which is ISO timestamp)
        buy_date = buy_date_str.split('T')[0]
        query = f"SELECT MAX(high) as peak_price FROM cw_history WHERE symbol = '{symbol}' AND date >= '{buy_date}'"
        df = pd.read_sql(query, engine)
        if not df.empty and pd.notna(df['peak_price'].iloc[0]):
            return max(float(df['peak_price'].iloc[0]), buy_price)
    except Exception as e:
        print(f"⚠️ Warning fetching peak price since buy for {symbol}: {e}")
    return buy_price

def scan_and_trade(force: bool = False, username: str = "demo", approved_symbols: list = None) -> list:
    """
    Scan the latest quant report, verify signals, and execute HOSE trading rules.
    1. Triggers STOP LOSS and DYNAMIC exits.
    2. Triggers pre-maturity exits (days to maturity < 10 days).
    3. Triggers BUY entries for high-scoring underpriced warrants.
       If approved_symbols is provided, only executes BUY for symbols in that list.
    """
    log_actions = []
    
    # Load market data from DB
    from src.modules.cw_pricing.backtest.reporter import load_opportunities_from_db
    df = load_opportunities_from_db(fallback_to_csv=True)
    if df.empty:
        log_actions.append("❌ Market data not available in DB or CSV. Run python run.py cw first to fetch market data!")
        return log_actions
        
    # ── Step 0: Detect HMM Market Regime ───────────────────────────
    mkt_regime = {"regime": "BULLISH_VOL_EXPANSION", "state": 1, "bias": "LONG_CW"}
    try:
        from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        mkt_regime = calculate_vnindex_regime()
        regime_name = mkt_regime.get("regime", "UNKNOWN")
        regime_bias = mkt_regime.get("bias", "LONG_CW")
        print(f"🌐 MARKET REGIME DETECTED: {regime_name} ({regime_bias})")
    except Exception as e:
        print(f"⚠️ Regime Detection failed: {e}. Falling back to V5.2 Defensive.")

    # Check market hours
    market_open = is_market_open()
    if not market_open and not force:
        log_actions.append("💤 Market is currently CLOSED (HOSE trading hours).")
        log_actions.append("💡 Use '--force' flag to override and simulate orders using last match prices.")
        return log_actions
        
    portfolio = load_portfolio(username=username)
    live_prices = dict(zip(df["A_MaCW"], df["C_GiaCW"]))
    live_days = dict(zip(df["A_MaCW"], df["L_Ngay"]))
    
    # Additional dynamic data for advanced exits
    live_ivs = dict(zip(df["A_MaCW"], df["S_IV_Pct"]))
    live_hvs = dict(zip(df["A_MaCW"], df["S_HV_Pct"]))
    live_deltas = dict(zip(df["A_MaCW"], df["T_Delta"]))
    live_gearings = dict(zip(df["A_MaCW"], df["F_DonBay"]))
    
    print("\n🔍 Checking active positions for exit triggers (Risk Management & Vol Arbitrage)...")
    # 1. Evaluate Exit Triggers
    held_symbols = list(portfolio["positions"].keys())
    for symbol in held_symbols:
        pos = portfolio["positions"][symbol]
        
        # Get live metrics
        live_price = live_prices.get(symbol, 0.0)
        days_left = int(live_days.get(symbol, pos["days_at_buy"]))
        iv_pct = live_ivs.get(symbol, 0.0)
        hv_pct = live_hvs.get(symbol, 0.0)
        warrant_delta = abs(float(live_deltas.get(symbol, 0.5)))
        warrant_gearing = float(live_gearings.get(symbol, 5.0))
        
        if live_price <= 0:
            continue
            
        p_l_pct = (live_price - pos["buy_price"]) / pos["buy_price"]
        peak_price = get_peak_price_since_buy(symbol, pos["buy_date"], pos["buy_price"])
        
        # Fetch underlying technical indicators dynamically
        underlying = pos.get("underlying")
        tech_metrics = get_underlying_technical_metrics(underlying)
        latest_stock_close = tech_metrics["latest_close"]
        ema15_val = tech_metrics["ema15"]
        atrr14 = tech_metrics["atrr14"]

        # ── Step 8.1: Master AI Distress Check for Existing Positions (from DB) ──
        ai_force_sell = False
        try:
            from src.core.database import SessionLocal as _SL, CompanyDistressAnalysis as _CDA
            _db3 = _SL()
            try:
                _health = (
                    _db3.query(_CDA)
                    .filter(_CDA.ticker == underlying)
                    .order_by(_CDA.year.desc())
                    .first()
                )
                if _health is not None:
                    _dp = float(_health.distress_probability or 0.0)
                    if _health.is_distressed == 1 or _dp > 0.50:
                        ai_force_sell = True
            finally:
                _db3.close()
        except Exception:
            pass
                
        if ai_force_sell:
             res = execute_sell(symbol, live_price, f"FORCE SELL: AI Credit Distress Triggered for {underlying}", username=username)
             log_actions.append(res["message"])
             continue
             
        # ── V5.3 ADAPTIVE EXIT PARAMETERS ──────────────────────────
        # Switch TP logic: Fixed 50% in Bull-Normal, Dynamic in Turbulent
        is_momentum_regime = mkt_regime["regime"] in ["BULLISH_VOL_CONTRACTION", "BULLISH_VOL_EXPANSION"]
        current_tp_pct = V51_TAKE_PROFIT_PCT if is_momentum_regime else V52_TAKE_PROFIT_PCT

        # 1. Take Profit check
        if p_l_pct >= current_tp_pct:
            reason = f"TAKE PROFIT HIT (V5.3 {'Momentum' if is_momentum_regime else 'Defensive'}: +{current_tp_pct*100:.0f}%)"
            log_actions.append(execute_sell(symbol, live_price, reason, username=username)["message"])
            continue

        # 2. Dynamic SL trigger (VaR based)
        try:
            from src.modules.regime_analysis.indicators.garch_evt_var import get_conformal_calibrated_var
            underlying_var = get_conformal_calibrated_var(underlying, current_state=mkt_regime["state"], alpha=0.95)
            sl_pct = max(0.08, min(0.25, underlying_var * warrant_gearing * 0.95))
            if not is_momentum_regime: sl_pct *= 0.7 # Tighter SL in bad regimes
        except:
            sl_pct = 0.20 # Fallback
            
        if p_l_pct <= -sl_pct:
            log_actions.append(execute_sell(symbol, live_price, f"STOP LOSS HIT (-{sl_pct*100:.1f}%)", username=username)["message"])
            continue
            
        # 3. Volatility Convergence Exit (ONLY in non-momentum regimes)
        if not is_momentum_regime and iv_pct > 0 and hv_pct > 0 and iv_pct >= hv_pct and p_l_pct > 0.05:
             log_actions.append(execute_sell(symbol, live_price, f"VOLATILITY CONVERGED (IV {iv_pct:.1f}% >= HV {hv_pct:.1f}%)", username=username) ["message"])
             continue
            
        # 4. CPCS EMA15 Trend Exit (Always active to catch wave end)
        if latest_stock_close is not None and ema15_val is not None and latest_stock_close < ema15_val and p_l_pct < 0.30:
            log_actions.append(execute_sell(symbol, live_price, f"TREND BREAKDOWN (Stock < EMA15)", username=username)["message"])
            continue

        # 5. Trailing Stop Exit (chỉ kích hoạt khi giá đã tăng vượt +8% từ điểm mua)
        elif peak_price >= pos["buy_price"] * 1.08 and live_price <= peak_price * 0.93:
            log_actions.append(execute_sell(symbol, live_price, f"TRAILING STOP HIT (7% drop from peak | P/L: {p_l_pct*100:.1f}%)", username=username)["message"])
            continue
            
        # 6. Expiry decay trigger
        elif days_left < MATURITY_LIMIT_DAYS:
            log_actions.append(execute_sell(symbol, live_price, f"PRE-MATURITY EXIT ({days_left}N)", username=username)["message"])
            continue
            
    # Reload portfolio state after potential sales
    portfolio = load_portfolio(username=username)
    
    # 2. Evaluate Entry Signals
    if mkt_regime.get("bias") == "SKIP_CW":
        log_actions.append("🚫 REGIME BLOCK: HMM detects high systemic risk. Entry suspended.")
        return log_actions

    print("🔍 Scanning market report for BUY signals...")
    # V5.3 Adaptive Entry: In Bullish bias, we also accept standard 'BUY' signals
    allowed_signals = ["STRONG BUY"]
    if mkt_regime.get("bias") == "LONG_CW":
        allowed_signals.append("BUY")
        allowed_signals.append("VOL ARBITRAGE BUY")
        
    buy_signals = df[df["U_Signal"].isin(allowed_signals)].sort_values("G_Score", ascending=False)
    
    # Apply AI Committee approval filter if provided
    if approved_symbols is not None:
        buy_signals = buy_signals[buy_signals["A_MaCW"].isin(approved_symbols)]
        if buy_signals.empty and approved_symbols:
            print("⚠️ No STRONG BUY signals matched the AI Committee approved list.")
    
    for _, row in buy_signals.iterrows():
        # Check portfolio slots
        if len(portfolio["positions"]) >= 5:
            break  # Max positions reached (5 slots)
            
        symbol = row["A_MaCW"]
        underlying = row["B_MaCPCS"]
        price = float(row["C_GiaCW"])
        score = float(row["G_Score"])
        days_left = int(row["L_Ngay"])
        
        # V5.3 Adaptive Note
        is_momentum_regime = mkt_regime["regime"] in ["BULLISH_VOL_CONTRACTION", "BULLISH_VOL_EXPANSION"]
        size_note = "V5.3 Static 15%" if is_momentum_regime else "V5.3 Dynamic Kelly"
        
        # Execute HOSE buy
        res = execute_buy(symbol, underlying, price, score, days_left, username=username, mkt_regime=mkt_regime)
        if res["status"] == "success":
            log_actions.append(res["message"] + f" | {size_note}")
            # Reload portfolio
            portfolio = load_portfolio(username=username)
            
    if not log_actions:
        log_actions.append("➖ No trades executed. Portfolio is fully balanced.")
        
    return log_actions

def print_portfolio_dashboard():
    """Print a highly polished, terminal-friendly quantitative trading dashboard."""
    portfolio = load_portfolio()
    
    # Load latest prices and metrics from DB to calculate active NAV
    live_prices = {}
    live_deltas = {}
    live_ratios = {}
    try:
        from src.modules.cw_pricing.backtest.reporter import load_opportunities_from_db
        df = load_opportunities_from_db(fallback_to_csv=True)
        if not df.empty:
            live_prices = dict(zip(df["A_MaCW"], df["C_GiaCW"]))
            live_deltas = dict(zip(df["A_MaCW"], df["T_Delta"]))
            live_ratios = dict(zip(df["A_MaCW"], df["hidden_ratio"]))
    except Exception:
        pass
            
    # Calculate metrics
    cash = portfolio["cash"]
    pos_val = 0.0
    active_rows = []
    
    now = datetime.now()
    
    for sym, pos in portfolio["positions"].items():
        curr_price = live_prices.get(sym, pos["buy_price"])
        val = pos["qty"] * curr_price
        pos_val += val
        
        p_l_vnd = val - pos["total_cost"]
        p_l_pct = (curr_price - pos["buy_price"]) / pos["buy_price"] * 100
        
        # Calculate Delta-Neutral Hedge Requirement
        delta = live_deltas.get(sym, 0.0)
        ratio_raw = live_ratios.get(sym, 1.0)
        
        try:
            if isinstance(ratio_raw, str) and ':' in ratio_raw:
                ratio = float(ratio_raw.split(':')[0])
            else:
                ratio = float(ratio_raw)
        except Exception:
            ratio = 1.0
            
        if ratio == 0: ratio = 1.0
        hedge_qty = (pos["qty"] / ratio) * abs(delta)
        hedge_str = f"Short {int(hedge_qty):,} CPCS" if hedge_qty > 0 else "N/A"
        
        # Format purchase and settlement dates (compact %d/%m format)
        buy_dt = datetime.fromisoformat(pos["buy_date"])
        buy_str = buy_dt.strftime("%d/%m")
        
        settlement_dt = datetime.fromisoformat(pos["settlement_date"])
        settle_str = settlement_dt.strftime("%d/%m")
        
        status = "🟢 TRADEABLE" if now >= settlement_dt else f"🔒 LOCKED T+2"
        
        sign = "+" if p_l_vnd >= 0 else ""
        active_rows.append({
            "Mã CW": sym,
            "Cổ Phiếu CS": pos["underlying"],
            "Số Lượng": f"{pos['qty']:,}",
            "Giá Mua": f"{pos['buy_price']:,.0f}đ",
            "Giá Hiện Tại": f"{curr_price:,.0f}đ",
            "Ngày Mua": buy_str,
            "Hàng Về": settle_str,
            "Vốn Đầu Tư": f"{pos['total_cost']:,.0f}đ",
            "Giá Trị": f"{val:,.0f}đ",
            "P/L": f"{sign}{p_l_vnd:,.0f}đ ({sign}{p_l_pct:.1f}%)",
            "Phòng hộ (Delta Hedge)": hedge_str,
            "Trạng Thái": status
        })
        
    total_nav = cash + pos_val
    initial = portfolio["initial_cash"]
    cum_p_l = total_nav - initial
    cum_p_l_pct = (total_nav - initial) / initial * 100
    
    # Calculate historical stats
    history = portfolio.get("history", [])
    completed_trades = [t for t in history if t["type"] == "SELL"]
    win_trades = [t for t in completed_trades if t.get("p_l_vnd", 0) > 0]
    
    win_rate = (len(win_trades) / len(completed_trades) * 100) if completed_trades else 0.0
    
    print("\n" + "=" * 125)
    print(" 🏆 FINVISTA QUANTITATIVE CO-WORKER: PAPER TRADING & LIVE VALIDATION DASHBOARD")
    print("=" * 125)
    print(f" Account Status: DEMO PAPER ACCOUNT | Currency: VND (Vietnamese Dong)")
    print("-" * 125)
    print(f"  Vốn Ban Đầu:   {initial:16,.0f}đ  |  Tiền Mặt (Cash): {cash:16,.0f}đ")
    print(f"  Giá Trị Mã:    {pos_val:16,.0f}đ  |  Tổng Tài Sản (NAV): {total_nav:16,.0f}đ")
    
    sign = "+" if cum_p_l >= 0 else ""
    print(f"  Lợi Nhuận lũy kế: {sign}{cum_p_l:,.0f}đ ({sign}{cum_p_l_pct:.2f}%)")
    print(f"  Tỷ Lệ Thắng (Win Rate): {win_rate:.1f}% ({len(win_trades)} thắng / {len(completed_trades)} lệnh đã đóng)")
    print("=" * 125)
    
    # Active positions table
    print("\n📊 CÁC VỊ THẾ ĐANG NẮM GIỮ CHỦ ĐỘNG (Active Positions):")
    if active_rows:
        df_active = pd.DataFrame(active_rows)
        print("-" * 125)
        print(df_active.to_string(index=False))
        print("-" * 125)
    else:
        print("  [Không có vị thế nào đang mở. Tài khoản đang nắm giữ 100% tiền mặt.]")
        
    # Transaction history table (last 8 transactions)
    print("\n📜 NHẬT KÝ 8 GIAO DỊCH GẦN NHẤT (Recent Transaction Logs):")
    if history:
        history_rows = []
        for t in reversed(history[-8:]):
            p_l_str = "N/A"
            if t["type"] == "SELL":
                p_l = t.get("p_l_vnd", 0.0)
                p_l_pct = t.get("p_l_pct", 0.0)
                sign = "+" if p_l >= 0 else ""
                p_l_str = f"{sign}{p_l:,.0f}đ ({sign}{p_l_pct:.1f}%)"
                
            date_dt = datetime.fromisoformat(t["date"])
            date_str = date_dt.strftime("%d/%m %H:%M")
            
            history_rows.append({
                "Thời Gian": date_str,
                "Mã CW": t["symbol"],
                "Lệnh": f" {t['type']} ",
                "Số Lượng": f"{t['qty']:,}",
                "Giá Khớp": f"{t['price']:,.0f}đ",
                "Phí & Thuế": f"{t['fee']:,.0f}đ",
                "Lợi Nhuận": p_l_str,
                "Lý Do / Mô Tả": t["reason"]
            })
        df_hist = pd.DataFrame(history_rows)
        print("-" * 125)
        print(df_hist.to_string(index=False))
        print("-" * 125)
    else:
        print("  [Nhật ký giao dịch trống. Chưa có lệnh nào được thực hiện.]")
    print("=" * 125 + "\n")
