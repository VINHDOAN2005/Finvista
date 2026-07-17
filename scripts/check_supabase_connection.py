#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Supabase connection and verify if tables have data
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

print(f"🔗 Connecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    session = sessionmaker(bind=engine)()
    
    # Test connection
    session.execute(text("SELECT 1"))
    print("✅ Successfully connected to Supabase!")
    
    # List of tables to check
    tables = [
        "users",
        "portfolios", 
        "positions",
        "transaction_history",
        "portfolio_nav_history",
        "market_opportunities",
        "cw_history",
        "stock_history"
    ]
    
    print("\n📊 Checking table data:")
    print("=" * 60)
    
    has_data = False
    for table in tables:
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            status = "✅" if count > 0 else "⚪"
            print(f"{status} {table:30s} : {count:,} rows")
            if count > 0:
                has_data = True
        except Exception as e:
            print(f"❌ {table:30s} : Error - {str(e)[:50]}")
    
    print("=" * 60)
    
    if has_data:
        print("\n✅ Supabase database has data - migration likely completed")
    else:
        print("\n⚠️  Supabase database is empty - migration needed")
    
    session.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)
