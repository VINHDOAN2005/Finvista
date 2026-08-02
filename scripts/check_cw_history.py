#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check CW historical data in database
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
    
    symbol = "CACB2511"
    
    print(f"\n🔍 Checking CW historical data for: {symbol}")
    print("=" * 60)
    
    # Check if cw_history table exists and has data
    result = session.execute(text(
        "SELECT COUNT(*) FROM cw_history WHERE symbol = :symbol"
    ), {"symbol": symbol}).scalar()
    
    if result > 0:
        print(f"✅ Found {result} rows in cw_history")
        
        # Get sample data
        rows = session.execute(text(
            "SELECT date, open, high, low, close, volume FROM cw_history WHERE symbol = :symbol ORDER BY date DESC LIMIT 5"
        ), {"symbol": symbol}).fetchall()
        
        print(f"\n📊 Sample data (last 5 rows):")
        for row in rows:
            print(f"   {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} V:{row[5]}")
    else:
        print(f"❌ No data found in cw_history for {symbol}")
    
    # Check if table exists
    tables = session.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE '%history%'
    """)).fetchall()
    
    print(f"\n📋 Available history tables:")
    for row in tables:
        print(f"   - {row[0]}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
