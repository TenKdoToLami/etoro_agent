import sqlite3
import json
from datetime import datetime
from dateutil import tz
from ..config import PORTFOLIO_DB_PATH

class SnapshotManager:
    def __init__(self, db_path=PORTFOLIO_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    date TEXT PRIMARY KEY,
                    equity REAL,
                    cash REAL,
                    invested REAL,
                    positions_json TEXT
                )
            ''')
            conn.commit()

    def take_snapshot(self, etoro_api):
        try:
            now = datetime.now(tz.gettz("America/New_York"))
            date_str = now.strftime('%Y-%m-%d')
            
            pnl = etoro_api.get_pnl()
            client_portfolio = pnl.get("clientPortfolio", {})
            
            cash = client_portfolio.get("credit", 0.0)
            positions = client_portfolio.get("positions", [])
            
            # simplified total invested
            total_invested = sum(p.get("amount", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
            unrealized_pnl = sum(p.get("unrealizedPnL", {}).get("pnL", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
            equity = cash + total_invested + unrealized_pnl
            
            positions_json = json.dumps(positions)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO daily_snapshots (date, equity, cash, invested, positions_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (date_str, equity, cash, total_invested, positions_json))
                conn.commit()
                
            return equity, cash, total_invested, len(positions)
        except Exception as e:
            from ..utils.logger import setup_logger
            setup_logger("snapshot_manager").error(f"Failed to take portfolio snapshot: {e}")
            return 0, 0, 0, 0
