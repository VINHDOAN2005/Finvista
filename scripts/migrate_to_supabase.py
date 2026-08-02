#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite to PostgreSQL Migration Script for Finvista
Migrates data from local SQLite to Supabase PostgreSQL
"""

import sqlite3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

# SQLite connection
SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finvista.db")
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

# PostgreSQL connection (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    print("Please set DATABASE_URL=postgresql://user:password@host:port/database")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

pg_engine = create_engine(DATABASE_URL)
pg_session = sessionmaker(bind=pg_engine)()

def migrate_table(table_name):
    """Migrate data from SQLite table to PostgreSQL"""
    print(f"📦 Migrating {table_name}...")
    
    # Get data from SQLite
    cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    # Get columns in PostgreSQL table
    try:
        res = pg_session.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = :table"
        ), {"table": table_name})
        pg_columns = [r[0] for r in res.fetchall()]
    except Exception as e:
        print(f"   ❌ Error fetching PostgreSQL columns for {table_name}: {e}")
        return

    # Use only columns that exist in both tables
    common_columns = [col for col in columns if col in pg_columns]
    if not common_columns:
        print(f"   ⚠️  No common columns found for {table_name}, skipping...")
        return
    
    # Convert to list of dicts
    data = [dict(row) for row in rows]
    
    # Insert into PostgreSQL
    try:
        if data:
            pg_session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            pg_session.commit()
            
            # Bulk insert in chunks using dynamic multi-row VALUES clauses
            columns_str = ", ".join(common_columns)
            chunk_size = 1000
            
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                placeholders_rows = []
                params = {}
                for row_idx, row in enumerate(chunk):
                    row_placeholders = []
                    for col in common_columns:
                        param_name = f"{col}_{row_idx}"
                        row_placeholders.append(f":{param_name}")
                        params[param_name] = row[col] if col in row else None
                    placeholders_rows.append(f"({', '.join(row_placeholders)})")
                
                sql = f"INSERT INTO {table_name} ({columns_str}) VALUES {', '.join(placeholders_rows)}"
                pg_session.execute(text(sql), params)
            
            pg_session.commit()
            print(f"   ✅ Migrated {len(data)} rows from {table_name}")
    except Exception as e:
        pg_session.rollback()
        print(f"   ❌ Error migrating {table_name}: {e}")

def main():
    print("🚀 Starting SQLite → PostgreSQL migration...")
    print(f"📥 Source: {SQLITE_DB}")
    print(f"📤 Target: {DATABASE_URL}")
    print("=" * 60)
    
    # List of tables to migrate (in order of dependencies)
    tables = [
        "users",
        "portfolios", 
        "positions",
        "transaction_history",
        "portfolio_nav_history",
        "market_opportunities",
        "cw_history",
        "stock_history",
        "ai_analysis_memory",
        "corporate_news",
        "corporate_events",
        "company_distress_analysis",
        "company_financials",
        "corporate_merton_credit",
        "cw_info",
        "macro_history",
        "vn30_gamma_exposure",
        "garch_vol_report"
    ]
    
    for table in tables:
        try:
            migrate_table(table)
        except Exception as e:
            print(f"❌ Failed to migrate {table}: {e}")
            continue
    
    print("=" * 60)
    print("✅ Migration completed!")
    
    sqlite_conn.close()
    pg_session.close()

if __name__ == "__main__":
    main()
