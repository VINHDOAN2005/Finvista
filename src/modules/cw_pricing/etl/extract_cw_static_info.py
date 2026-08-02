# -*- coding: utf-8 -*-
"""
FINVISTA: CW STATIC INFO EXTRACTOR
====================================
Cào thông tin tĩnh (Strike, Maturity, Ratio, Issuer...) cho tất cả 
Covered Warrants lịch sử từ trang Vietstock chung-quyen.htm.

Source: https://finance.vietstock.vn/chung-khoan-phai-sinh/{SYM}/chung-quyen.htm
Output: DB table `cw_info` + CSV backup

Author: samvo / Finvista
"""
import os, sys, re, json, time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import engine
from sqlalchemy import text

# ── CONFIG ────────────────────────────────────────────────────────
REQUEST_DELAY   = 1.2   # giây giữa mỗi request
MAX_RETRIES     = 3     # số lần retry khi timeout/lỗi
BATCH_SIZE      = 50    # số mã mỗi batch trước khi flush vào DB
OUTPUT_CSV      = 'data/processed/cw_static_info.csv'
# ──────────────────────────────────────────────────────────────────

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'Referer': 'https://finance.vietstock.vn/',
}


def parse_date_vn(s):
    """Chuyển dd/mm/yyyy → yyyy-mm-dd. Trả None nếu không parse được."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def parse_number(s):
    """Chuyển '31,400' → 31400.0"""
    if not s:
        return None
    try:
        return float(s.replace(',', '').replace('.', '').strip())
    except (ValueError, AttributeError):
        return None


def parse_ratio(s):
    """Chuyển '4 : 1' → 4.0"""
    if not s:
        return None
    m = re.search(r'(\d+)\s*:\s*(\d+)', str(s))
    if m:
        try:
            return float(m.group(1)) / float(m.group(2))
        except ZeroDivisionError:
            return None
    try:
        return float(str(s).replace(',', ''))
    except ValueError:
        return None


def fetch_cw_info(symbol: str, session: requests.Session) -> dict | None:
    """
    Cào thông tin tĩnh của một mã CW từ Vietstock.
    Trả về dict hoặc None nếu thất bại.
    """
    url = f'https://finance.vietstock.vn/chung-khoan-phai-sinh/{symbol}/chung-quyen.htm'

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                return None
            break
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            return None
    else:
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')
    right_panel = soup.find(class_='overview-right')
    if not right_panel:
        return None

    # Parse key-value pairs từ panel
    raw_text = right_panel.get_text(separator='|', strip=True)

    def extract(pattern, text=raw_text, group=1):
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return m.group(group).strip() if m else None

    # Extract fields
    underlying    = extract(r'CK cơ sở\|:\|([A-Z0-9]+)')
    issuer_cw     = extract(r'Tổ chức phát hành CW\|:\|(.+?)\|Loại')
    cw_type       = extract(r'Loại chứng quyền\|:\|(\w+)')
    exercise_type = extract(r'Kiểu thực hiện\|:\|([^|]+)')
    duration      = extract(r'Thời hạn\|:\|([^|]+)')
    issue_date    = extract(r'Ngày phát hành\|:\|(\d{2}/\d{2}/\d{4})')
    list_date     = extract(r'Ngày niêm yết\|:\|(\d{2}/\d{2}/\d{4})')
    first_date    = extract(r'Ngày giao dịch đầu tiên\|:\|(\d{2}/\d{2}/\d{4})')
    last_date     = extract(r'Ngày giao dịch cuối cùng\|:\|(\d{2}/\d{2}/\d{4})')
    maturity_date = extract(r'Ngày đáo hạn\|:\|(\d{2}/\d{2}/\d{4})')
    ratio_raw     = extract(r'Tỷ lệ chuyển đổi\|:\|([0-9\s:,]+)')
    issue_price   = extract(r'Giá phát hành\|:\|([0-9,\.]+)')
    strike_raw    = extract(r'Giá thực hiện\|:\|([0-9,\.]+)')
    listed_vol    = extract(r'Khối lượng Niêm yết\|:\|([0-9,\.]+)')

    # Clean issuer name (remove trailing parens junk)
    if issuer_cw:
        issuer_cw = re.sub(r'\(.*$', '', issuer_cw).strip()
        issuer_cw = issuer_cw.strip('|').strip()

    return {
        'symbol':           symbol,
        'underlying':       underlying,
        'issuer':           issuer_cw,
        'cw_type':          cw_type,           # Mua / Bán
        'exercise_style':   exercise_type,     # Châu Âu / Mỹ
        'duration':         duration,
        'issue_date':       parse_date_vn(issue_date),
        'listing_date':     parse_date_vn(list_date),
        'first_trade_date': parse_date_vn(first_date),
        'last_trade_date':  parse_date_vn(last_date),
        'maturity_date':    parse_date_vn(maturity_date),
        'conversion_ratio': parse_ratio(ratio_raw),
        'issue_price':      parse_number(issue_price),
        'strike_price':     parse_number(strike_raw),
        'listed_volume':    parse_number(listed_vol),
        'crawled_at':       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def ensure_db_table():
    """Tạo bảng cw_info nếu chưa có."""
    ddl = """
    CREATE TABLE IF NOT EXISTS cw_info (
        symbol           TEXT PRIMARY KEY,
        underlying       TEXT,
        issuer           TEXT,
        cw_type          TEXT,
        exercise_style   TEXT,
        duration         TEXT,
        issue_date       TEXT,
        listing_date     TEXT,
        first_trade_date TEXT,
        last_trade_date  TEXT,
        maturity_date    TEXT,
        conversion_ratio REAL,
        issue_price      REAL,
        strike_price     REAL,
        listed_volume    REAL,
        crawled_at       TEXT
    )
    """
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()


def upsert_to_db(records: list[dict]):
    """Insert or replace records vào bảng cw_info."""
    if not records:
        return
    df = pd.DataFrame(records)
    df.to_sql('cw_info', engine, if_exists='append', index=False,
              method='multi')


def get_already_crawled() -> set:
    """Lấy danh sách mã đã crawl trong DB."""
    try:
        df = pd.read_sql('SELECT symbol FROM cw_info', engine)
        return set(df['symbol'].tolist())
    except Exception:
        return set()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Crawl CW static info từ Vietstock')
    parser.add_argument('--master', default='data/raw/discovered_cw_master_list.csv',
                        help='File danh sách mã CW cần crawl')
    parser.add_argument('--limit', type=int, default=0,
                        help='Giới hạn số mã (0 = tất cả)')
    parser.add_argument('--refresh', action='store_true',
                        help='Crawl lại kể cả mã đã có trong DB')
    args = parser.parse_args()

    # Đọc danh sách mã CW
    master_df = pd.read_csv(args.master)
    symbols = master_df['symbol'].tolist()
    if args.limit > 0:
        symbols = symbols[:args.limit]

    # Tạo bảng DB
    ensure_db_table()

    # Lọc mã đã crawl (nếu không refresh)
    already = set() if args.refresh else get_already_crawled()
    to_crawl = [s for s in symbols if s not in already]

    print('=' * 70)
    print(f'  CW STATIC INFO CRAWLER — Vietstock chung-quyen.htm')
    print(f'  Tổng mã: {len(symbols)} | Cần crawl: {len(to_crawl)} | Đã có: {len(already)}')
    print('=' * 70)

    session = requests.Session()
    session.headers.update(HEADERS)

    results = []
    success = fail = skip = 0

    for i, sym in enumerate(to_crawl, 1):
        prefix = f'[{i}/{len(to_crawl)}] {sym}'
        info = fetch_cw_info(sym, session)

        if info:
            # Check dữ liệu đủ không
            if info.get('strike_price') and info.get('maturity_date'):
                results.append(info)
                print(f'{prefix} | Strike={info["strike_price"]:,.0f} | Maturity={info["maturity_date"]} | Ratio={info["conversion_ratio"]}')
                success += 1
            else:
                # Vẫn lưu dù thiếu một số trường
                results.append(info)
                missing = [k for k in ['strike_price','maturity_date','conversion_ratio'] if not info.get(k)]
                print(f'{prefix} | PARTIAL (thiếu: {", ".join(missing)})')
                success += 1
        else:
            print(f'{prefix} | FAIL (không tải được trang)')
            fail += 1

        # Flush vào DB mỗi BATCH_SIZE mã
        if len(results) >= BATCH_SIZE:
            try:
                upsert_to_db(results)
                results = []
            except Exception as e:
                print(f'  [DB ERROR] {e}')

        time.sleep(REQUEST_DELAY)

    # Flush phần còn lại
    if results:
        try:
            upsert_to_db(results)
        except Exception as e:
            print(f'  [DB ERROR final] {e}')

    # Export CSV backup
    try:
        df_all = pd.read_sql('SELECT * FROM cw_info ORDER BY symbol', engine)
        df_all.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f'\nBackup CSV: {OUTPUT_CSV} ({len(df_all)} records)')
    except Exception as e:
        print(f'CSV export error: {e}')

    print()
    print('=' * 70)
    print(f'  DONE! Success={success} | Fail={fail} | Total crawled={success+fail}')
    print(f'  DB: bảng cw_info đã cập nhật')
    print('=' * 70)


if __name__ == '__main__':
    main()
