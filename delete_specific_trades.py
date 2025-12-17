
import sqlite3

def clean_trades():
    db_path = 'd:\\BIAS-ATR-Grid-Trader\\grid_state.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check existing records to confirm format
    print("Checking records for sh510300...")
    cursor.execute("SELECT * FROM trade_history WHERE code='sh510300'")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    # 2. Define targets to delete
    # User provided:
    # 2025-12-15T12:08:08	sh510300	卖出	3.150	1000	150.00
    # 2025-12-15T12:08:08	sz159915	卖出	2.450	500	25.00
    # 2025-12-14T12:08:08	sh510500	卖出	2.880	800	-80.00
    
    # Note: '卖出' is 'SELL' in DB based on typical logic, but let's check direction column 
    # from the print above. If user says '卖出', the system likely stores 'SELL'.
    
    targets = [
        {'code': 'sh510300', 'price': 3.150, 'volume': 1000, 'ts_fragment': '2025-12-15'},
        {'code': 'sz159915', 'price': 2.450, 'volume': 500,  'ts_fragment': '2025-12-15'},
        {'code': 'sh510500', 'price': 2.880, 'volume': 800,  'ts_fragment': '2025-12-14'}
    ]
    
    deleted_count = 0
    
    for t in targets:
        # Construct query to be flexible with timestamp exact match vs partial
        # We match code, price (approx), and volume
        sql = """
            DELETE FROM trade_history 
            WHERE code=? 
            AND abs(price - ?) < 0.001 
            AND volume=?
            AND timestamp LIKE ?
        """
        cursor.execute(sql, (t['code'], t['price'], t['volume'], f"%{t['ts_fragment']}%"))
        deleted_count += cursor.rowcount
        
    conn.commit()
    print(f"Total deleted rows: {deleted_count}")
    conn.close()

if __name__ == "__main__":
    clean_trades()
