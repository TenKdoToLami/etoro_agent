import argparse
import sys
from pprint import pprint

from .core.etoro import EtoroAPI
from .data.market import DataManager
from .config import ETORO_USER_KEY, ETORO_API_KEY
from .daily_job import main as run_daily_job

def get_api():
    if not ETORO_USER_KEY or ETORO_USER_KEY == "your_agent_portfolio_user_token_here":
        print("Error: ETORO_USER_KEY not set in .env")
        sys.exit(1)
    return EtoroAPI(api_key=ETORO_API_KEY, user_key=ETORO_USER_KEY)

def main():
    parser = argparse.ArgumentParser(description="eToro Agent Portfolio CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("status", help="Check if market is open according to yfinance")
    
    subparsers.add_parser("portfolio", help="Show current equity, cash, and invested amounts")
    
    subparsers.add_parser("positions", help="List all open positions")
    
    buy_parser = subparsers.add_parser("buy", help="Open a new position")
    buy_parser.add_argument("--symbol", type=str, required=True, help="Symbol to buy (e.g. SPY)")
    buy_parser.add_argument("--amount", type=float, required=True, help="Amount in USD to invest")
    
    sell_parser = subparsers.add_parser("sell", help="Close a position")
    sell_parser.add_argument("--id", type=str, required=True, help="Position ID to close")
    
    subparsers.add_parser("run-job", help="Execute the daily trading job manually")
    
    args = parser.parse_args()
    
    if args.command == "status":
        dm = DataManager()
        is_open = dm.is_market_open_today()
        print(f"Market Status: {'OPEN / DATA AVAILABLE' if is_open else 'CLOSED / NO DATA'}")
        
    elif args.command == "portfolio":
        api = get_api()
        pnl = api.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})
        credit = client_portfolio.get("credit", 0.0)
        positions = client_portfolio.get("positions", [])
        total_invested = sum(p.get("amount", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        unrealized_pnl = sum(p.get("unrealizedPnL", {}).get("pnL", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        print(f"Equity:   ${credit + total_invested + unrealized_pnl:.2f}")
        print(f"Cash:     ${credit:.2f}")
        print(f"Invested: ${total_invested:.2f}")
        
    elif args.command == "positions":
        api = get_api()
        pnl = api.get_pnl()
        positions = pnl.get("clientPortfolio", {}).get("positions", [])
        manual_positions = [p for p in positions if p.get("mirrorID", 0) == 0]
        if not manual_positions:
            print("No open positions.")
        else:
            for p in manual_positions:
                print(f"ID: {p.get('positionID')} | InstrumentID: {p.get('instrumentID')} | Amount: ${p.get('amount')} | PnL: ${p.get('unrealizedPnL', {}).get('pnL', 0)}")
                
    elif args.command == "buy":
        api = get_api()
        try:
            instrument_id = api.resolve_instrument(args.symbol)
            print(f"Resolved {args.symbol} to Instrument ID {instrument_id}. Opening position...")
            res = api.open_position(instrument_id, args.amount)
            print("Success:")
            pprint(res)
        except Exception as e:
            print(f"Failed to open position: {e}")
            
    elif args.command == "sell":
        api = get_api()
        try:
            print(f"Closing position ID {args.id}...")
            res = api.close_position(args.id)
            print("Success:")
            pprint(res)
        except Exception as e:
            print(f"Failed to close position: {e}")
            
    elif args.command == "run-job":
        run_daily_job()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
