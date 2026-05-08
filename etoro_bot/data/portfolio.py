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
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rebalance_log (
                    date TEXT PRIMARY KEY,
                    weights_json TEXT,
                    regime TEXT
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

    def get_last_rebalance(self):
        """Returns (date_str, weights_dict, regime_str) of the last recorded rebalance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT date, weights_json, regime FROM rebalance_log ORDER BY date DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    return row[0], json.loads(row[1]), row[2]
        except Exception as e:
            from ..utils.logger import setup_logger
            setup_logger("snapshot_manager").error(f"Failed to get last rebalance: {e}")
        return None, None, None

    def log_rebalance(self, date_str, weights, regime):
        """Logs a new rebalance event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO rebalance_log (date, weights_json, regime)
                    VALUES (?, ?, ?)
                ''', (date_str, json.dumps(weights), regime))
                conn.commit()
        except Exception as e:
            from ..utils.logger import setup_logger
            setup_logger("snapshot_manager").error(f"Failed to log rebalance: {e}")
