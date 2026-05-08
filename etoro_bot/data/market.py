import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from ..config import DB_PATH
from dateutil import tz

class DataManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS spy_daily (
                    date TEXT PRIMARY KEY,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    vix REAL
                )
            ''')
            # Migration: Check if vix column exists, if not add it
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(spy_daily)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'vix' not in columns:
                conn.execute('ALTER TABLE spy_daily ADD COLUMN vix REAL DEFAULT 15.0')
            conn.commit()

    def is_market_open_today(self):
        now = datetime.now(tz.gettz("America/New_York"))
        if now.weekday() >= 5: # Saturday or Sunday
            return False
            
        spy = yf.Ticker("SPY")
        today_str = now.strftime('%Y-%m-%d')
        df = spy.history(period="1d")
        if df.empty:
            return False
            
        last_date = df.index[-1].strftime('%Y-%m-%d')
        return last_date == today_str

    def update_historical_data(self):
        """Fetches missing data including VIX and Yields."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM spy_daily")
            last_date = cursor.fetchone()[0]
        
        period = "7d" if last_date else "1y"
        
        from ..utils.logger import setup_logger
        logger = setup_logger("market_data")
        logger.info(f"Updating historical data (SPY, VIX) for period: {period}")

        spy_df = yf.Ticker("SPY").history(period=period)
        vix_df = yf.Ticker("^VIX").history(period=period)
        
        with sqlite3.connect(self.db_path) as conn:
            for date, row in spy_df.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                
                # Align VIX and Spread
                vix_val = vix_df.loc[date]['Close'] if date in vix_df.index else 15.0
                
                conn.execute('''
                    INSERT OR REPLACE INTO spy_daily (date, open, high, low, close, volume, vix)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (date_str, row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume']), float(vix_val)))
            conn.commit()

    def get_historical_data(self):
        now = datetime.now(tz.gettz("America/New_York"))
        today_str = now.strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM spy_daily WHERE date < ? ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=(today_str,))
            
        history = []
        for _, row in df.iterrows():
            history.append({
                "date": row['date'],
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume'],
                "vix": row['vix']
            })
        return history

    def get_todays_price(self):
        """Gets today's intraday data including macro indicators."""
        spy = yf.Ticker("SPY")
        df = spy.history(period="1d", interval="1m")
        if df.empty:
            return None
        vix = yf.Ticker("^VIX").fast_info['last_price']
            
        return {
            "date": df.index[-1].strftime('%Y-%m-%d'),
            "open": float(df['Open'].iloc[0]),
            "high": float(df['High'].max()),
            "low": float(df['Low'].min()),
            "close": float(df['Close'].iloc[-1]),
            "volume": int(df['Volume'].sum()),
            "vix": float(vix)
        }
