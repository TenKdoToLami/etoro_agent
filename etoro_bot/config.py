import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file (now in parent directory)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

ETORO_API_KEY = os.getenv("ETORO_API_KEY", "sdgdskldFPLGfjHn1421dgnlxdGTbngdflg6290bRjslfihsjhSDsdgGHH25hjf")
ETORO_USER_KEY = os.getenv("ETORO_USER_KEY")

SAFETY_CASH = float(os.getenv("SAFETY_CASH", "20.0"))
MIN_POSITION_VALUE = float(os.getenv("MIN_POSITION_VALUE", "40.0"))

# Strategy parameters
REBALANCE_INTERVAL_DAYS = int(os.getenv("REBALANCE_INTERVAL_DAYS", "20"))
VIX_THRESHOLD = float(os.getenv("VIX_THRESHOLD", "32.0"))

# Bullish symbols (leveraged ETFs)
SYMBOL_SPY = os.getenv("SYMBOL_SPY", "SPY")
SYMBOL_SPYU = os.getenv("SYMBOL_SPYU", "SPYU")
SYMBOL_UPRO = os.getenv("SYMBOL_UPRO", "UPRO")
SYMBOL_TECL = os.getenv("SYMBOL_TECL", "TECL")
SYMBOL_TNA = os.getenv("SYMBOL_TNA", "TNA")
SYMBOL_TQQQ = os.getenv("SYMBOL_TQQQ", "TQQQ")
SYMBOL_UDOW = os.getenv("SYMBOL_UDOW", "UDOW")

# Panic symbols (safe havens)
SYMBOL_GOLD = os.getenv("SYMBOL_GOLD", "GOLD")
SYMBOL_TLT = os.getenv("SYMBOL_TLT", "TLT")
SYMBOL_SHY = os.getenv("SYMBOL_SHY", "BIL")

# Cash / bond parking
SYMBOL_CASH = os.getenv("SYMBOL_CASH", "BND")

# Database paths (now in parent directory by default)
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "data.sqlite"))
PORTFOLIO_DB_PATH = os.getenv("PORTFOLIO_DB_PATH", str(Path(__file__).parent.parent / "portfolio.sqlite"))

STATE_TO_SYMBOL = {
    # Bullish assets
    "SPYU": SYMBOL_SPYU,
    "UPRO": SYMBOL_UPRO,
    "TECL": SYMBOL_TECL,
    "TNA": SYMBOL_TNA,
    "TQQQ": SYMBOL_TQQQ,
    "UDOW": SYMBOL_UDOW,
    # Panic assets
    "GOLD": SYMBOL_GOLD,
    "TLT": SYMBOL_TLT,
    "SHY": SYMBOL_SHY,
    # Other
    "CASH": SYMBOL_CASH,
}
