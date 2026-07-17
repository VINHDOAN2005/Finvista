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

# Default file paths
PORTFOLIO_FILE = os.path.join("data", "paper_portfolio.json")
REPORT_PATH = os.path.join("data", "excel_cw_report.csv")

# Trading constants
INITIAL_CASH = 100_000_000.0  # 100 Million VND
BUY_FEE_RATE = 0.0015         # 0.15%
SELL_FEE_RATE = 0.0025        # 0.15% fee + 0.1% tax = 0.25%
HOSE_LOT_SIZE = 100           # Minimum trading lot
MAX_ALLOCATION_PCT = 0.20     # Max 20% of total portfolio value per position

# Strategy thresholds
TAKE_PROFIT_PCT = 0.20        # +20% TP
STOP_LOSS_PCT = -0.15         # -15% SL
MATURITY_LIMIT_DAYS = 10      # Exit position if < 10 days left to maturity

def load_portfolio(username: str = "demo") -> dict:
    """Load or initialize the paper trading portfolio using the SQL database."""
    from src.common.database import SessionLocal, User, Portfolio, Position, TransactionHistory
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # Check if this is demo, fallback to init_db
            if username == "demo":
                from src.common.database import init_db
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
        
    from src.common.database import SessionLocal, User, Portfolio, Position, TransactionHistory
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
            
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ SQLite save error: {e}")
    finally:
        db.close()

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

def execute_buy(symbol: str, underlying: str, price: float, score: float, days_left: int, username: str = "demo") -> dict:
    """Execute a HOSE-compliant BUY order."""
    portfolio = load_portfolio(username=username)
    
    if price <= 0:
        return {"status": "error", "message": f"❌ Invalid market price {price}đ for {symbol}."}
        
    # Check if we already hold this position
    if symbol in portfolio["positions"]:
        return {"status": "error", "message": f"⚠️ Already holding position in {symbol}."}
        
    # Check if the CW is close to expiry
    if days_left < MATURITY_LIMIT_DAYS:
        return {"status": "error", "message": f"⏩ Skipping {symbol} (Days to maturity {days_left} is below limit {MATURITY_LIMIT_DAYS} days)."}

    # Live prices dictionary to calculate current NAV
    live_prices = {symbol: price}
    total_nav = get_portfolio_value(portfolio, live_prices)
    
    # Capital allocation rules
    max_alloc_value = total_nav * MAX_ALLOCATION_PCT
    target_purchase_val = min(max_alloc_value, portfolio["cash"])
    
    if target_purchase_val < (price * HOSE_LOT_SIZE):
        return {"status": "error", "message": f"❌ Insufficient cash to buy even 1 lot of {symbol}."}
        
    # Calculate quantity in multiples of 100
    raw_qty = target_purchase_val / (price * (1 + BUY_FEE_RATE))
    qty = int(raw_qty // HOSE_LOT_SIZE) * HOSE_LOT_SIZE
    
    if qty <= 0:
        return {"status": "error", "message": f"❌ Cash limit too low to allocate 1 full lot (100 CWs) for {symbol}."}
        
    # Calculate costs
    gross_value = qty * price
    fee = gross_value * BUY_FEE_RATE
    total_cost = gross_value + fee
    
    if total_cost > portfolio["cash"]:
        # Safety rollback by 1 lot
        qty -= HOSE_LOT_SIZE
        gross_value = qty * price
        fee = gross_value * BUY_FEE_RATE
        total_cost = gross_value + fee
        if qty <= 0:
            return {"status": "error", "message": f"❌ Insufficient cash after fee calculations."}

    # Deduct cash
    portfolio["cash"] -= total_cost
    
    # Store position
    now_str = datetime.now().isoformat()
    portfolio["positions"][symbol] = {
        "symbol": symbol,
        "underlying": underlying,
        "qty": qty,
        "buy_price": price,
        "buy_date": now_str,
        "settlement_date": calculate_settlement_date(now_str),
        "total_cost": total_cost,
        "score_at_buy": score,
        "days_at_buy": days_left
    }
    
    # Add to transaction history
    portfolio["history"].append({
        "symbol": symbol,
        "underlying": underlying,
        "type": "BUY",
        "qty": qty,
        "price": price,
        "value": gross_value,
        "fee": fee,
        "date": now_str,
        "reason": f"Volatility Arbitrage Signal (Score: {score:.1f})"
    })
    
    save_portfolio(portfolio, username=username)
    return {
        "status": "success",
        "message": f"🛍️ BOUGHT {qty:,} {symbol} at {price:,.0f}đ | Total Cost: {total_cost:,.0f}đ (Fee: {fee:,.0f}đ)"
    }

def execute_sell(symbol: str, price: float, reason: str, username: str = "demo") -> dict:
    """Execute a HOSE-compliant SELL order, respecting T+2.5 settlement locks."""
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
            "message": f"🔒 Position in {symbol} is locked in T+2.5 settlement cycle! Available to sell in {hours_left:.1f} hours."
        }
        
    # Calculate proceeds
    gross_value = qty * price
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
        "price": price,
        "value": gross_value,
        "fee": fee_and_tax,
        "date": now.isoformat(),
        "reason": reason,
        "buy_price": pos["buy_price"],
        "p_l_vnd": net_proceeds - pos["total_cost"],
        "p_l_pct": (price - pos["buy_price"]) / pos["buy_price"] * 100
    })
    
    save_portfolio(portfolio, username=username)
    p_l = net_proceeds - pos["total_cost"]
    p_l_pct = (price - pos["buy_price"]) / pos["buy_price"] * 100
    
    sign = "+" if p_l >= 0 else ""
    return {
        "status": "success",
        "message": f"💸 SOLD {qty:,} {symbol} at {price:,.0f}đ | Net Received: {net_proceeds:,.0f}đ | P/L: {sign}{p_l:,.0f}đ ({sign}{p_l_pct:.2f}%) | Reason: {reason}"
    }

def scan_and_trade(force: bool = False, username: str = "demo") -> list:
    """
    Scan the latest quant report, verify signals, and execute HOSE trading rules.
    1. Triggers STOP LOSS and TAKE PROFIT exits.
    2. Triggers pre-maturity exits (days to maturity < 10 days).
    3. Triggers BUY entries for high-scoring underpriced warrants.
    """
    log_actions = []
    
    # Verify report existence
    if not os.path.exists(REPORT_PATH):
        log_actions.append("❌ Core analysis report not found. Run python run_cw.py first to fetch market data!")
        return log_actions
        
    df = pd.read_csv(REPORT_PATH)
    if df.empty:
        log_actions.append("❌ Empty market report. Run analysis first.")
        return log_actions
        
    # Check market hours
    market_open = is_market_open()
    if not market_open and not force:
        log_actions.append("💤 Market is currently CLOSED (HOSE trading: Mon-Fri, 9:00-11:30 & 13:00-14:45).")
        log_actions.append("💡 Use '--force' flag to override and simulate orders using last match prices.")
        return log_actions
        
    portfolio = load_portfolio(username=username)
    live_prices = dict(zip(df["A_MaCW"], df["C_GiaCW"]))
    live_days = dict(zip(df["A_MaCW"], df["L_Ngay"]))
    
    print("\n🔍 Checking active positions for exit triggers (Risk Management)...")
    # 1. Evaluate Exit Triggers
    held_symbols = list(portfolio["positions"].keys())
    for symbol in held_symbols:
        pos = portfolio["positions"][symbol]
        
        # Get live price
        live_price = live_prices.get(symbol, 0.0)
        days_left = int(live_days.get(symbol, pos["days_at_buy"]))
        
        if live_price <= 0:
            continue
            
        p_l_pct = (live_price - pos["buy_price"]) / pos["buy_price"]
        
        # SL trigger
        if p_l_pct <= STOP_LOSS_PCT:
            res = execute_sell(symbol, live_price, f"STOP LOSS HIT ({p_l_pct*100:.1f}%)", username=username)
            log_actions.append(res["message"])
            
        # TP trigger
        elif p_l_pct >= TAKE_PROFIT_PCT:
            res = execute_sell(symbol, live_price, f"TAKE PROFIT HIT (+{p_l_pct*100:.1f}%)", username=username)
            log_actions.append(res["message"])
            
        # Expiry decay trigger
        elif days_left < MATURITY_LIMIT_DAYS:
            res = execute_sell(symbol, live_price, f"PRE-MATURITY EXIT (Days to Expiry: {days_left} < {MATURITY_LIMIT_DAYS} days)", username=username)
            log_actions.append(res["message"])
            
    # Reload portfolio state after potential sales
    portfolio = load_portfolio(username=username)
    
    # 2. Evaluate Entry Signals (Only buy if we have cash and slot)
    print("🔍 Scanning market report for BUY signals...")
    buy_signals = df[df["U_Signal"] == "STRONG BUY"].sort_values("G_Score", ascending=False)
    
    for _, row in buy_signals.iterrows():
        # Check cash and portfolio slots
        if len(portfolio["positions"]) >= (1 / MAX_ALLOCATION_PCT):
            break  # Max positions reached (5 slots at 20% allocation)
            
        symbol = row["A_MaCW"]
        underlying = row["B_MaCPCS"]
        price = float(row["C_GiaCW"])
        score = float(row["G_Score"])
        days_left = int(row["L_Ngay"])
        
        # Execute HOSE buy
        res = execute_buy(symbol, underlying, price, score, days_left, username=username)
        if res["status"] == "success":
            log_actions.append(res["message"])
            # Reload portfolio
            portfolio = load_portfolio(username=username)
            
    if not log_actions:
        log_actions.append("➖ No trades executed. Portfolio is fully balanced with current market signals.")
        
    return log_actions

def print_portfolio_dashboard():
    """Print a highly polished, terminal-friendly quantitative trading dashboard."""
    portfolio = load_portfolio()
    
    # Read latest prices from cache report to calculate active NAV
    live_prices = {}
    if os.path.exists(REPORT_PATH):
        try:
            df = pd.read_csv(REPORT_PATH)
            live_prices = dict(zip(df["A_MaCW"], df["C_GiaCW"]))
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
