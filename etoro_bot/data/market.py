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
                    volume INTEGER
                )
            ''')
            conn.commit()

    def is_market_open_today(self):
        # We'll use yfinance to see if there is data for today.
        # Alternatively, pandas_market_calendars could be used if installed.
        # For a simple check, we see if today is a weekday and not a major holiday by trying to fetch today's data.
        now = datetime.now(tz.gettz("America/New_York"))
        if now.weekday() >= 5: # Saturday or Sunday
            return False
            
        # Check if there's any data for today
        spy = yf.Ticker("SPY")
        today_str = now.strftime('%Y-%m-%d')
        # Fetch data for today to see if it exists (market open/recently closed)
        df = spy.history(period="1d")
        if df.empty:
            return False
            
        # If the last available date in the df matches today's date in NY, market was/is open today
        last_date = df.index[-1].strftime('%Y-%m-%d')
        return last_date == today_str

    def update_historical_data(self):
        """Fetches up to 1 year of data to populate the database."""
        spy = yf.Ticker("SPY")
        df = spy.history(period="1y")
        
        with sqlite3.connect(self.db_path) as conn:
            for date, row in df.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                conn.execute('''
                    INSERT OR REPLACE INTO spy_daily (date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date_str, row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume'])))
            conn.commit()

    def get_historical_data(self):
        """Returns history up to yesterday. Today's data should be fetched separately as it's incomplete."""
        now = datetime.now(tz.gettz("America/New_York"))
        today_str = now.strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            # Get everything strictly before today
            query = "SELECT * FROM spy_daily WHERE date < ? ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=(today_str,))
            
        # Convert to list of dicts required by genome
        history = []
        for _, row in df.iterrows():
            history.append({
                "date": row['date'],
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume']
            })
        return history

    def get_todays_price(self):
        """Gets today's intraday data (the unclosed candle)."""
        spy = yf.Ticker("SPY")
        df = spy.history(period="1d", interval="1m")
        if df.empty:
            return None
            
        # Aggregate the intraday data into a single day candle
        return {
            "date": df.index[-1].strftime('%Y-%m-%d'),
            "open": float(df['Open'].iloc[0]),
            "high": float(df['High'].max()),
            "low": float(df['Low'].min()),
            "close": float(df['Close'].iloc[-1]), # Current mid-price
            "volume": int(df['Volume'].sum())
        }
