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

# Genome path (now in parent directory by default)
GENOME_PATH = os.getenv("GENOME_PATH", str(Path(__file__).parent.parent / "genome.json"))

SYMBOL_CASH = os.getenv("SYMBOL_CASH", "BND")
SYMBOL_SPY = os.getenv("SYMBOL_SPY", "SPY")
SYMBOL_2XSPY = os.getenv("SYMBOL_2XSPY", "SSO")
SYMBOL_3XSPY = os.getenv("SYMBOL_3XSPY", "UPRO")

# Database paths (now in parent directory by default)
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "data.sqlite"))
PORTFOLIO_DB_PATH = os.getenv("PORTFOLIO_DB_PATH", str(Path(__file__).parent.parent / "portfolio.sqlite"))

STATE_TO_SYMBOL = {
    "CASH": SYMBOL_CASH,
    "SPY": SYMBOL_SPY,
    "2xSPY": SYMBOL_2XSPY,
    "3xSPY": SYMBOL_3XSPY
}
