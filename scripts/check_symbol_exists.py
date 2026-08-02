#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if a warrant symbol exists in database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"🔗 Connecting to database...")

try:
    engine = create_engine(DATABASE_URL)
    session = sessionmaker(bind=engine)()
    
    # Check if symbol exists in market_opportunities
    symbol = "CACB2511"
    
    print(f"\n🔍 Checking for symbol: {symbol}")
    print("=" * 60)
    
    # Check market_opportunities
    result = session.execute(text(
        "SELECT symbol, underlying, price, decision_signal FROM market_opportunities WHERE symbol = :symbol"
    ), {"symbol": symbol}).fetchone()
    
    if result:
        print(f"✅ Found in market_opportunities:")
        print(f"   Symbol: {result[0]}")
        print(f"   Underlying: {result[1]}")
        print(f"   Price: {result[2]}")
        print(f"   Signal: {result[3]}")
    else:
        print(f"❌ Not found in market_opportunities")
    
    # Check cw_history
    result = session.execute(text(
        "SELECT COUNT(*) FROM cw_history WHERE symbol = :symbol"
    ), {"symbol": symbol}).scalar()
    
    if result > 0:
        print(f"✅ Found in cw_history: {result} rows")
    else:
        print(f"❌ Not found in cw_history")
    
    # List all available symbols that start with CA
    result = session.execute(text(
        "SELECT symbol FROM market_opportunities WHERE symbol LIKE 'CA%' ORDER BY symbol LIMIT 10"
    )).fetchall()
    
    print(f"\n📋 Available symbols starting with 'CA':")
    for row in result:
        print(f"   - {row[0]}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
